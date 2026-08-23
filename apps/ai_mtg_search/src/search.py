"""
Retrieval over Neon Postgres + pgvector.

Composes structured SQL filters with vector search rather than folding metadata
into one opaque index. Five decisions here come from measurements against the
live database, reproducible with eda.ipynb:

- Every vector query runs `exact=True`. The shared IVFFlat index spans all
  three embedding sources, so a `source`-filtered search loses recall, and the
  planner only picks the index below roughly LIMIT 10 — approximate results
  would come and go as `k` changed.
- Ordering always carries a secondary key. Short chunks (`'Flash'`) produce
  bit-identical distances across several cards.
- `card_text` searches exclude empty chunks; 366 faces have no oracle text and
  would otherwise match anything.
- Name resolution unions vector search with lexical fuzzy matching, because
  each misses cards the other finds.
- Results collapse to one row per card, since multi-faced cards store one row
  per face.
"""

import json
import threading

from rapidfuzz import fuzz, process

from src.constants import (
    SOURCE_CARD_NAME,
    SOURCE_CARD_TEXT,
    SOURCE_RULES,
)
from src.db.neon import query
from src.embeddings import embed_query
from src.utils.mtg_text import preprocess_oracle_text

# `commander_legal` is derived rather than stored; everything else is a column.
_CARD_COLUMNS = """
    c.scryfall_oracle_id,
    c.face_index,
    c.name,
    c.face_name,
    c.type_line,
    c.mana_cost,
    c.mana_value,
    c.color_identity,
    c.oracle_text,
    c.power,
    c.toughness,
    c.loyalty,
    c.keywords,
    c.layout,
    (c.legalities->>'commander') = 'Legal' AS commander_legal,
    c.edhrec_rank
"""

_JOIN_ON_EMBEDDING_ID = """
    JOIN cards c
      ON c.scryfall_oracle_id = split_part(e.id, ':', 1)
     AND c.face_index = split_part(e.id, ':', 2)::int
"""

NAME_CANDIDATES = 25
TEXT_CANDIDATES = 50

# Floor for accepting a fuzzy name match, on rapidfuzz's 0-100 WRatio scale.
# Measured separation: genuine misspellings land at 81-100, nonsense at 30-60.
MIN_NAME_SIMILARITY = 70


def _build_filters(
    *,
    types: list[str] | None = None,
    subtypes: list[str] | None = None,
    supertypes: list[str] | None = None,
    keywords: list[str] | None = None,
    types_all: list[str] | None = None,
    subtypes_all: list[str] | None = None,
    keywords_all: list[str] | None = None,
    color_identity: list[str] | None = None,
    layout: list[str] | None = None,
    max_mana_value: float | None = None,
    min_mana_value: float | None = None,
    commander_legal: bool = False,
    exclude_funny: bool = False,
) -> tuple[list[str], dict]:
    """
    Translate filter kwargs into SQL predicates on `cards`.

    Array columns come in two flavours because both are needed: `keywords`
    overlaps (`&&`, any of), while `keywords_all` contains (`@>`, all of).
    "Flying or vigilance" and "flying and vigilance" are different questions,
    and only the second answers "creatures with flying and vigilance".

    `color_identity` is contained the other way round (`<@`): asking for Dimir
    means cards playable in Dimir, not cards that happen to include blue.
    """
    clauses: list[str] = []
    params: dict = {}

    any_of = {"types": types, "subtypes": subtypes, "supertypes": supertypes, "keywords": keywords}
    all_of = {"types": types_all, "subtypes": subtypes_all, "keywords": keywords_all}

    for column, values in any_of.items():
        if values:
            clauses.append(f"c.{column} && %({column}_any)s::text[]")
            params[f"{column}_any"] = list(values)

    for column, values in all_of.items():
        if values:
            clauses.append(f"c.{column} @> %({column}_all)s::text[]")
            params[f"{column}_all"] = list(values)

    if color_identity is not None:
        clauses.append("c.color_identity <@ %(color_identity)s::text[]")
        params["color_identity"] = list(color_identity)

    if layout:
        clauses.append("c.layout = ANY(%(layout)s)")
        params["layout"] = list(layout)

    if max_mana_value is not None:
        clauses.append("c.mana_value <= %(max_mana_value)s")
        params["max_mana_value"] = max_mana_value

    if min_mana_value is not None:
        clauses.append("c.mana_value >= %(min_mana_value)s")
        params["min_mana_value"] = min_mana_value

    if commander_legal:
        clauses.append("(c.legalities->>'commander') = 'Legal'")

    if exclude_funny:
        clauses.append("NOT c.is_funny")

    return clauses, params


def dedupe_cards(rows: list[dict]) -> list[dict]:
    """
    Keep the best-ranked face of each card, preserving order.

    Multi-faced cards store one row per face, so an unfiltered result set can
    show the same card several times. Also used to union the per-ability
    searches on the seed-card path.
    """
    seen: set[str] = set()
    unique = []
    for row in rows:
        oracle_id = row["scryfall_oracle_id"]
        if oracle_id not in seen:
            seen.add(oracle_id)
            unique.append(row)
    return unique


def _vector_search(source: str, text: str, k: int, filters: dict) -> list[dict]:
    clauses, params = _build_filters(**filters)
    params["qvec"] = json.dumps(embed_query(text))
    # Over-fetch so face collapsing cannot shrink the result below k.
    params["limit"] = k * 2

    if source == SOURCE_CARD_TEXT:
        clauses.append("length(e.chunk_text) > 0")
    clauses.insert(0, "e.source = %(source)s")
    params["source"] = source

    rows = query(
        f"""
        SELECT {_CARD_COLUMNS},
               e.chunk_text,
               1 - (e.embedding <=> %(qvec)s::vector) AS similarity
        FROM embeddings e
        {_JOIN_ON_EMBEDDING_ID}
        WHERE {' AND '.join(clauses)}
        ORDER BY e.embedding <=> %(qvec)s::vector, c.name, c.face_index
        LIMIT %(limit)s
        """,
        params,
        exact=True,
    )
    return dedupe_cards(rows)[:k]


def search_card_text(query_text: str, k: int = TEXT_CANDIDATES, **filters) -> list[dict]:
    """
    Semantic search over preprocessed oracle text.

    Queries containing mana or tap notation are preprocessed the same way the
    ETL preprocessed the documents, so `{T}` lands near "Tap (tap this
    permanent)" instead of nowhere.
    """
    if "{" in query_text:
        query_text = preprocess_oracle_text(query_text)
    return _vector_search(SOURCE_CARD_TEXT, query_text, k, filters)


def search_card_name(query_text: str, k: int = NAME_CANDIDATES, **filters) -> list[dict]:
    """Semantic search over card names — handles paraphrase and most misspellings."""
    return _vector_search(SOURCE_CARD_NAME, query_text, k, filters)


def search_rules(query_text: str, k: int = 5) -> list[dict]:
    """
    Search the comprehensive rules and glossary.

    Available but not wired into the router, which still declines rules
    questions. Useful for expanding a query into keywords before a card search.
    """
    return query(
        """
        SELECT e.id, e.chunk_text,
               1 - (e.embedding <=> %(qvec)s::vector) AS similarity
        FROM embeddings e
        WHERE e.source = %(source)s
        ORDER BY e.embedding <=> %(qvec)s::vector, e.id
        LIMIT %(limit)s
        """,
        {
            "qvec": json.dumps(embed_query(preprocess_oracle_text(query_text) if "{" in query_text else query_text)),
            "source": SOURCE_RULES,
            "limit": k,
        },
        exact=True,
    )


def filter_cards(k: int = 50, **filters) -> list[dict]:
    """Structured lookup with no vector component, ordered by EDHREC popularity."""
    clauses, params = _build_filters(**filters)
    # Over-fetch so collapsing the faces of multi-faced cards cannot drop the
    # result below k.
    params["limit"] = k * 2
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = query(
        f"""
        SELECT {_CARD_COLUMNS}
        FROM cards c
        {where}
        ORDER BY c.edhrec_rank NULLS LAST, c.name, c.face_index
        LIMIT %(limit)s
        """,
        params,
    )
    return dedupe_cards(rows)[:k]


def lookup_card_exact(name: str) -> list[dict]:
    """Case-insensitive exact match on the full card name."""
    return query(
        f"""
        SELECT {_CARD_COLUMNS}
        FROM cards c
        WHERE lower(c.name) = lower(%(name)s)
        ORDER BY c.face_index
        """,
        {"name": name},
    )


# --------------------------------------------------------------------------- #
#  Name resolution                                                            #
# --------------------------------------------------------------------------- #

_name_cache: list[str] | None = None
_name_cache_lock = threading.Lock()


def _all_card_names() -> list[str]:
    """
    Every distinct card name, cached for the process lifetime.

    ~35k names, about a second to fetch. `pg_trgm` would let Postgres do this
    instead, but it is not installed and this app has no DDL rights.
    """
    global _name_cache
    with _name_cache_lock:
        if _name_cache is None:
            _name_cache = [row["name"] for row in query("SELECT DISTINCT name FROM cards")]
    return _name_cache


def _fuzzy_name_matches(name: str, limit: int = 10) -> list[str]:
    return [
        match
        for match, score, _ in process.extract(
            name, _all_card_names(), scorer=fuzz.WRatio, limit=limit
        )
        if score >= MIN_NAME_SIMILARITY
    ]


def _lexical_similarity(target: str, card: dict) -> float:
    """Best string similarity between the query and either name the card carries."""
    full = (card.get("name") or "").lower()
    face = (card.get("face_name") or card.get("name") or "").lower()
    return max(fuzz.WRatio(target, full), fuzz.WRatio(target, face))


def resolve_card(name: str) -> dict | None:
    """
    Resolve a user-supplied card name to a single card.

    Tries exact match first, then unions semantic search over `card_name` with
    lexical fuzzy matching over every card name. The two disagree usefully:
    vector search finds `rhystic` → Rhystic Study, fuzzy matching finds
    `Chaterfang` → Chatterfang, Squirrel General, and neither finds both.
    """
    if not name:
        return None

    exact = lookup_card_exact(name)
    if exact:
        return exact[0]

    candidates = search_card_name(name, k=NAME_CANDIDATES)
    known = {row["name"] for row in candidates}
    for fuzzy_name in _fuzzy_name_matches(name):
        if fuzzy_name not in known:
            rows = lookup_card_exact(fuzzy_name)
            if rows:
                candidates.append(rows[0])
                known.add(fuzzy_name)

    if not candidates:
        return None

    target = name.lower()

    def score(card: dict) -> float:
        """Blend lexical similarity with a substring and legality nudge."""
        full = (card.get("name") or "").lower()
        face = (card.get("face_name") or card.get("name") or "").lower()
        return (
            fuzz.WRatio(target, face) * 0.4
            + fuzz.WRatio(target, full) * 0.4
            + (15 if target in full else 0)
            + (5 if card.get("commander_legal") else 0)
        )

    best = max(candidates, key=score)

    # Vector search always returns its k nearest neighbours, however far away
    # they are, so without a floor a nonsense name resolves to an arbitrary
    # card. Real misspellings score 81-100 here; nonsense scores 30-60.
    if _lexical_similarity(target, best) < MIN_NAME_SIMILARITY:
        return None
    return best


def card_abilities(card: dict) -> list[str]:
    """
    Split a card's oracle text into individual abilities, preprocessed.

    This is the fix for one-card-many-functions: a card that ramps, gains life
    and draws blurs into a single vector, so each ability is searched
    separately. Preprocessing is required — raw oracle text is full of `{T}`
    and `{2}{R}` notation, while the document vectors hold the expanded form.
    """
    text = card.get("oracle_text")
    if not text:
        return []
    clean = preprocess_oracle_text(text, card_name=card.get("name"))
    return [line.strip() for line in clean.split("\n") if line.strip()]


# --------------------------------------------------------------------------- #
#  Presentation                                                               #
# --------------------------------------------------------------------------- #

def _combat_stats(card: dict) -> str | None:
    if card.get("power") is not None or card.get("toughness") is not None:
        return f"{card.get('power') or '?'}/{card.get('toughness') or '?'}"
    if card.get("loyalty") is not None:
        return f"loyalty {card['loyalty']}"
    return None


def _format_card(index: int, card: dict) -> str:
    """
    Render one candidate as labelled lines.

    Deliberately not a delimiter-separated table: oracle text genuinely
    contains '|' (d20 roll outcomes and Station thresholds, e.g.
    "1-6 | Add {R}{R}{R}{R}"), which in a pipe-delimited row silently becomes
    extra columns and shifts every later field. Line breaks bound each field
    instead, and the text is the last field on its line.
    """
    heading = f"{index}. {card['name']}"
    face = card.get("face_name")
    if face and face != card.get("name"):
        heading += f"  [matched face: {face}]"

    mana = card.get("mana_cost") or "no cost"
    mana_value = card.get("mana_value")
    if mana_value is not None:
        mana += f" (mv {mana_value:g})"

    fields = [
        ("type", card.get("type_line")),
        ("mana", mana),
        ("colors", "/".join(card.get("color_identity") or []) or "colorless"),
        ("stats", _combat_stats(card)),
        ("keywords", ", ".join(card.get("keywords") or [])),
        # Oracle text is internally newline-separated; flatten so one card
        # stays one block and the labels remain unambiguous.
        ("text", (card.get("oracle_text") or "").replace("\n", " / ")),
        ("commander", "legal" if card.get("commander_legal") else "not legal"),
        ("edhrec", card.get("edhrec_rank")),
    ]

    lines = [heading]
    lines.extend(f"   {label}: {value}" for label, value in fields if value)
    return "\n".join(lines)


def format_candidates(rows: list[dict]) -> str:
    """Render candidates as labelled blocks for the ranker prompt."""
    return "\n".join(_format_card(i, row) for i, row in enumerate(rows, 1))
