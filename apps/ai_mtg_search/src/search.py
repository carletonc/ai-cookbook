"""
Retrieval over Neon Postgres + pgvector.

Composes structured SQL filters with vector search rather than folding metadata
into one opaque index. Five decisions here come from measurements against the
live database, reproducible with notebooks/eda.ipynb:

- Every vector query runs `exact=True`. The shared IVFFlat index spans all
  three embedding sources, so a `source`-filtered search loses recall, and the
  planner only picks the index below roughly LIMIT 10 — approximate results
  would come and go as `k` changed.
- Ordering always carries a secondary key. Short chunks (`'Flash'`) produce
  bit-identical distances across several cards.
- `card_text` searches exclude empty chunks; 366 faces have no oracle text and
  would otherwise match anything.
- Name resolution tries exact title, then substring contains (for character
  names like Narset), then unions vector search with lexical fuzzy matching.
- Results collapse to one row per card, since multi-faced cards store one row
  per face.
"""

import json
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal

from rapidfuzz import fuzz, process

from src.constants import (
    LEGALITY_FORMATS,
    SOURCE_CARD_NAME,
    SOURCE_CARD_TEXT,
    SOURCE_RULES,
)
from src.db.cards import (
    CARD_COLUMNS,
    dedupe_cards,
    lookup_card_by_oracle_id,
    lookup_card_exact,
    lookup_cards_containing_name,
    merge_search_hits,
    sort_for_picker,
)
from src.db.neon import query
from src.embeddings import embed_query
from src.utils.mtg_text import preprocess_oracle_text

_JOIN_ON_EMBEDDING_ID = """
    JOIN cards c
      ON c.scryfall_oracle_id = split_part(e.id, ':', 1)
     AND c.face_index = split_part(e.id, ':', 2)::int
"""

# Opt-in log of vector SQL calls. Streamlit leaves this unset.
_vector_search_log: ContextVar[list | None] = ContextVar(
    "vector_search_log", default=None
)


def record_search_event(event: dict) -> None:
    """Append to the active `trace_vector_searches()` log, or no-op."""
    log = _vector_search_log.get()
    if log is not None:
        log.append(event)


@contextmanager
def trace_vector_searches():
    """Collect one event per vector SQL call (and union-dedupe) for inspection."""
    events: list[dict] = []
    token = _vector_search_log.set(events)
    try:
        yield events
    finally:
        _vector_search_log.reset(token)


NAME_CANDIDATES = 25
TEXT_CANDIDATES = 50

# Cosine floor on `card_text` vector search (similarity = 1 - <=> ).
# Name search and RapidFuzz name matching use different scales; do not reuse this.
MIN_TEXT_SIMILARITY = 0.6

# How many name-vector / RapidFuzz neighbours to consider before floor+gap.
# High enough that a typo of a large character line (Ajani, Jace) is not
# truncated before the gap filter runs.
FUZZY_NAME_POOL = 75

# Floor for accepting a fuzzy name match, on rapidfuzz's 0-100 WRatio scale.
# Measured separation: genuine misspellings land at 81-100, nonsense at 30-60.
MIN_NAME_SIMILARITY = 70

# After the floor, keep only scores within this many points of the best hit so
# a bad typo does not surface an entire neighbourhood of weak neighbours.
NAME_MATCH_GAP = 10

# Unique fuzzy hits at or above this skip the picker (e.g. Lightnin Bolt → Lightning
# Bolt at ~96). Weaker unique hits still ask the user — Narest → Narstad Scrapper
# at ~82 must not silently become a seed.
FUZZY_AUTO_ACCEPT = 90


def _build_filters(
    *,
    types: list[str] | None = None,
    subtypes: list[str] | None = None,
    supertypes: list[str] | None = None,
    keywords: list[str] | None = None,
    types_all: list[str] | None = None,
    subtypes_all: list[str] | None = None,
    keywords_all: list[str] | None = None,
    colors: list[str] | None = None,
    colors_all: list[str] | None = None,
    color_identity: list[str] | None = None,
    layout: list[str] | None = None,
    max_mana_value: float | None = None,
    min_mana_value: float | None = None,
    legal_in: str | list[str] | None = None,
    commander_legal: bool = False,
    exclude_funny: bool = False,
) -> tuple[list[str], dict]:
    """
    Translate filter kwargs into SQL predicates on `cards`.

    Every kwarg is a real column (or a JSONB key on `legalities`). The planner
    does not emit these yet; `search_card_text(..., **filters)` and
    `filter_cards` already accept them.

    Array columns come in two flavours: `keywords` overlaps (`&&`, any of),
    while `keywords_all` contains (`@>`, all of). "Flying or vigilance" and
    "flying and vigilance" are different questions.

    `color_identity` is contained the other way (`<@`): Dimir means cards
    playable in Dimir. `colors` is the face's actual color and uses `&&` /
    `@>` like types.

    `legal_in` checks `legalities->>format = 'Legal'` (MTGJson capitalization).
    `commander_legal=True` is sugar for `legal_in='commander'`.
    """
    clauses: list[str] = []
    params: dict = {}

    any_of = {
        "types": types,
        "subtypes": subtypes,
        "supertypes": supertypes,
        "keywords": keywords,
        "colors": colors,
    }
    all_of = {
        "types": types_all,
        "subtypes": subtypes_all,
        "keywords": keywords_all,
        "colors": colors_all,
    }

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

    formats: list[str] = []
    if legal_in:
        formats.extend([legal_in] if isinstance(legal_in, str) else list(legal_in))
    if commander_legal:
        formats.append("commander")
    seen_formats: set[str] = set()
    for i, fmt in enumerate(formats):
        key = fmt.strip().lower()
        if key not in LEGALITY_FORMATS or key in seen_formats:
            continue
        seen_formats.add(key)
        param = f"legal_fmt_{i}"
        clauses.append(f"(c.legalities->>%({param})s) = 'Legal'")
        params[param] = key

    if exclude_funny:
        clauses.append("NOT c.is_funny")

    return clauses, params


def _vector_search(source: str, text: str, k: int, filters: dict) -> list[dict]:
    clauses, params = _build_filters(**filters)
    params["qvec"] = json.dumps(embed_query(text))
    # Over-fetch so face collapsing cannot shrink the result below k.
    params["limit"] = k * 2

    if source == SOURCE_CARD_TEXT:
        clauses.append("length(e.chunk_text) > 0")
        clauses.append(
            "(1 - (e.embedding <=> %(qvec)s::vector)) >= %(min_sim)s"
        )
        params["min_sim"] = MIN_TEXT_SIMILARITY
    clauses.insert(0, "e.source = %(source)s")
    params["source"] = source

    rows = query(
        f"""
        SELECT {CARD_COLUMNS},
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
    unique = dedupe_cards(rows)
    if source == SOURCE_CARD_TEXT:
        unique = [
            row
            for row in unique
            if row.get("similarity") is not None
            and float(row["similarity"]) >= MIN_TEXT_SIMILARITY
        ]
    result = unique[:k]
    record_search_event(
        {
            "event": "vector_sql",
            "source": source,
            "input": text,
            "k": k,
            "min_similarity": MIN_TEXT_SIMILARITY if source == SOURCE_CARD_TEXT else None,
            "sql_limit": k * 2,
            "sql_rows": len(rows),
            "after_face_dedupe": len(unique),
            "returned": len(result),
            "names": [row["name"] for row in result],
        }
    )
    return result


def search_card_text(query_text: str, k: int = TEXT_CANDIDATES, **filters) -> list[dict]:
    """
    Semantic search over preprocessed oracle text.

    One vector query, one string. Queries containing mana or tap notation are
    preprocessed the same way the ETL preprocessed the documents, so `{T}`
    lands near "Tap (tap this permanent)" instead of nowhere.
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
        SELECT {CARD_COLUMNS}
        FROM cards c
        {where}
        ORDER BY c.edhrec_rank NULLS LAST, c.name, c.face_index
        LIMIT %(limit)s
        """,
        params,
    )
    return dedupe_cards(rows)[:k]


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
    Loaded on the first typo path only — not on the landing page.
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


def _fuzzy_seed_candidates(name: str) -> tuple[list[dict], float | None]:
    """
    Union name-vector search with lexical fuzzy matches.

    Apply floor, then gap from the best score. Every unique card that survives
    is returned — no artificial top-N (same idea as the contains picker).
    """
    candidates = search_card_name(name, k=FUZZY_NAME_POOL)
    known = {row["name"] for row in candidates}
    for fuzzy_name in _fuzzy_name_matches(name, limit=FUZZY_NAME_POOL):
        if fuzzy_name not in known:
            rows = lookup_card_exact(fuzzy_name)
            if rows:
                candidates.append(rows[0])
                known.add(fuzzy_name)

    target = name.lower()
    scored = [
        (_lexical_similarity(target, card), card)
        for card in candidates
    ]
    scored = [(score, card) for score, card in scored if score >= MIN_NAME_SIMILARITY]
    if not scored:
        return [], None

    best = max(score for score, _ in scored)
    kept = [
        card
        for score, card in scored
        if best - score <= NAME_MATCH_GAP
    ]
    return sort_for_picker(dedupe_cards(kept)), best


@dataclass(frozen=True)
class SeedMatchResult:
    """Cards that match a seed name, plus how they were found."""

    cards: list[dict]
    source: Literal["exact", "contains", "fuzzy"]
    # Best lexical score among fuzzy candidates; else None.
    best_score: float | None = None


def find_seed_matches(name: str) -> SeedMatchResult:
    """
    Resolve a seed-card name to zero, one, or many cards.

    Order: exact full title → case-insensitive contains on name/face_name →
    fuzzy + name-vector fallback for typos (floor + gap over a large neighbour
    pool). Callers show a picker when appropriate; `source` selects the prompt.
    """
    if not name or not name.strip():
        return SeedMatchResult(cards=[], source="exact")

    name = name.strip()

    exact = lookup_card_exact(name)
    if exact:
        return SeedMatchResult(cards=dedupe_cards(exact), source="exact")

    contains = lookup_cards_containing_name(name)
    if contains:
        return SeedMatchResult(cards=contains, source="contains")

    cards, best = _fuzzy_seed_candidates(name)
    return SeedMatchResult(cards=cards, source="fuzzy", best_score=best)


def resolve_card(name: str) -> dict | None:
    """
    Resolve a user-supplied card name to a single card, or None.

    Prefer `find_seed_matches` when the caller can show a picker. This helper
    keeps the old one-winner behaviour for scripts and smoke tests: unique
    match only; multiple matches return None rather than guessing.
    """
    matches = find_seed_matches(name)
    if len(matches.cards) == 1:
        return matches.cards[0]
    return None


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

    fields = [
        ("type", card.get("type_line")),
        ("mana", card.get("mana_cost") or "no cost"),
        # Numeric converted cost for ranking only. The prompt forbids echoing
        # this as "mv N"; write-ups should cite the printed `mana` line.
        (
            "mana value",
            None if card.get("mana_value") is None else f"{card['mana_value']:g}",
        ),
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


# Re-export card lookups so callers can keep importing from search if needed.
__all__ = [
    "TEXT_CANDIDATES",
    "MIN_TEXT_SIMILARITY",
    "FUZZY_AUTO_ACCEPT",
    "SeedMatchResult",
    "card_abilities",
    "dedupe_cards",
    "filter_cards",
    "find_seed_matches",
    "format_candidates",
    "lookup_card_by_oracle_id",
    "lookup_card_exact",
    "lookup_cards_containing_name",
    "merge_search_hits",
    "resolve_card",
    "search_card_name",
    "search_card_text",
    "search_rules",
    "trace_vector_searches",
    "record_search_event",
]
