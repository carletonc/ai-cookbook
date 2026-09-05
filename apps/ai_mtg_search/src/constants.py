"""
Schema constants for the Neon `cards` table.

Column names are snake_case, one row per card face, primary key
`(scryfall_oracle_id, face_index)`. The previous MTGJson camelCase projection
(`cardName`, `legalities.commander`) is gone — that shape belonged to the local
ETL, which now lives in the `mtg-db` repo, where the full column list is
defined.
"""

# Kwargs on `_build_filters` → `cards` columns. Planner does not emit these
# yet; keep the names identical to the schema so wiring later is mechanical.
FILTER_LABELS = {
    "types": "Card Type",
    "subtypes": "Subtype",
    "supertypes": "Supertype",
    "keywords": "Keyword",
    "colors": "Colors",
    "color_identity": "Color Identity",
    "layout": "Layout",
    "min_mana_value": "Min Mana Value",
    "max_mana_value": "Max Mana Value",
    "legal_in": "Legal in format",
    "commander_legal": "Commander Legal Only",
    "exclude_funny": "Exclude joke cards",
}

# JSONB keys observed on `cards.legalities`. Values are 'Legal' / 'Banned'.
LEGALITY_FORMATS = frozenset(
    {
        "alchemy",
        "brawl",
        "commander",
        "duel",
        "future",
        "gladiator",
        "historic",
        "legacy",
        "modern",
        "oathbreaker",
        "oldschool",
        "pauper",
        "paupercommander",
        "penny",
        "pioneer",
        "predh",
        "premodern",
        "standard",
        "standardbrawl",
        "timeless",
        "vintage",
    }
)

COLOR_IDENTITY = {
    "W": "White",
    "U": "Blue",
    "B": "Black",
    "R": "Red",
    "G": "Green",
}

# Vector sources in the shared `embeddings` table. Choosing the wrong one is
# not recoverable by tuning: `card_text` holds oracle text only, so a name
# query aimed at it matches cards that merely *mention* the name — searching
# `card_text` for "Lightning Bolt" never returns Lightning Bolt.
SOURCE_CARD_NAME = "card_name"
SOURCE_CARD_TEXT = "card_text"
SOURCE_RULES = "rules"
