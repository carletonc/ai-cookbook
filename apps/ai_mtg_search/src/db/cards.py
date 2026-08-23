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
    show the same card several times.
    """
    seen: set[str] = set()
    unique = []
    for row in rows:
        oracle_id = row["scryfall_oracle_id"]
        if oracle_id not in seen:
            seen.add(oracle_id)
            unique.append(row)
    return unique


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
