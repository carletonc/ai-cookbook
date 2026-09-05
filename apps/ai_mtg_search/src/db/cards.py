"""
Structured lookups on the Neon `cards` table.

Vector search stays in `src.search`. This module is the SQL half: exact name,
substring name (for disambiguation), and resume-by-oracle-id after a pick.
"""

from src.db.neon import query

# `commander_legal` is derived rather than stored; everything else is a column.
CARD_COLUMNS = """
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


def dedupe_cards(rows: list[dict]) -> list[dict]:
    """
    Keep the best-ranked face of each card, preserving order.

    Multi-faced cards store one row per face, so an unfiltered result set can
    show the same card several times. First occurrence wins — callers that
    `ORDER BY` distance should pass rows in that order.
    """
    seen: set[str] = set()
    unique = []
    for row in rows:
        oracle_id = row["scryfall_oracle_id"]
        if oracle_id not in seen:
            seen.add(oracle_id)
            unique.append(row)
    return unique


def merge_search_hits(rows: list[dict], *, limit: int | None = None) -> list[dict]:
    """
    Collapse hits from several vector queries to one row per card.

    The same oracle id can appear in more than one batch (e.g. one search per
    ability). Keep the higher `similarity`; ties keep the earlier row. The
    caller never sees duplicate oracle ids.
    """
    best: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        oracle_id = row["scryfall_oracle_id"]
        prev = best.get(oracle_id)
        if prev is None:
            best[oracle_id] = row
            order.append(oracle_id)
            continue
        prev_sim = prev.get("similarity")
        new_sim = row.get("similarity")
        if new_sim is not None and (prev_sim is None or float(new_sim) > float(prev_sim)):
            best[oracle_id] = row
    merged = [best[oid] for oid in order]
    if limit is not None:
        return merged[:limit]
    return merged


def _norm_oracle_text(card: dict) -> str:
    return " ".join((card.get("oracle_text") or "").split()).lower()


def drop_equivalent_to_seed(seed: dict, cards: list[dict]) -> list[dict]:
    """
    Drop the seed and color-shifted / playtest copies of the same rules text.

    Dedupe is by oracle id only; White Rhystic Study is a different id with
    the same oracle text, so it would otherwise rank as the best alternative.
    """
    seed_id = seed.get("scryfall_oracle_id")
    seed_text = _norm_oracle_text(seed)
    kept = []
    for card in cards:
        if card.get("scryfall_oracle_id") == seed_id:
            continue
        if seed_text and _norm_oracle_text(card) == seed_text:
            continue
        kept.append(card)
    return kept


def legal_cards_first(cards: list[dict]) -> list[dict]:
    """Stable: commander-legal rows stay in order, then the rest."""
    return sorted(cards, key=lambda card: 0 if card.get("commander_legal") else 1)


def sort_for_picker(rows: list[dict]) -> list[dict]:
    """Commander-legal first, then alphabetical by name (stable for the picker)."""
    return sorted(
        rows,
        key=lambda card: (
            0 if card.get("commander_legal") else 1,
            (card.get("name") or "").lower(),
        ),
    )


def lookup_card_exact(name: str) -> list[dict]:
    """Case-insensitive exact match on the full card name."""
    return query(
        f"""
        SELECT {CARD_COLUMNS}
        FROM cards c
        WHERE lower(c.name) = lower(%(name)s)
        ORDER BY c.face_index
        """,
        {"name": name},
    )


def lookup_cards_containing_name(fragment: str) -> list[dict]:
    """
    Case-insensitive substring match on printed name or face name.

    Used when the user types a character name ("Narset", "Ajani") rather than
    a full title. Oracle text is not searched. Results are ordered for the
    picker: commander-legal first, then name.
    """
    if not fragment or not fragment.strip():
        return []

    rows = query(
        f"""
        SELECT {CARD_COLUMNS}
        FROM cards c
        WHERE c.name ILIKE %(pattern)s
           OR c.face_name ILIKE %(pattern)s
        """,
        {"pattern": f"%{fragment.strip()}%"},
    )
    return sort_for_picker(dedupe_cards(rows))


def lookup_card_by_oracle_id(oracle_id: str) -> dict | None:
    """Load one card by Scryfall oracle id (first face). Used after a picker choice."""
    if not oracle_id:
        return None
    rows = query(
        f"""
        SELECT {CARD_COLUMNS}
        FROM cards c
        WHERE c.scryfall_oracle_id = %(oracle_id)s
        ORDER BY c.face_index
        LIMIT 1
        """,
        {"oracle_id": oracle_id},
    )
    return rows[0] if rows else None
