# Metadata field definitions with their types and descriptions
METADATA_FIELDS = {
    # Core identification
    'name': {
        'type': 'string',
        'description': 'Card name',
        'filterable': True,
        'display_name': 'Name'
    },
    'oracle_id': {
        'type': 'string',
        'description': 'Unique Scryfall Oracle ID',
        'filterable': False,
        'display_name': 'Oracle ID'
    },
    'layout': {
        'type': 'string',
        'description': 'Card layout type (normal, split, flip, etc.)',
        'filterable': True,
        'display_name': 'Layout'
    },
    'face_name': {
        'type': 'string',
        'description': 'Name of this face (for multi-faced cards)',
        'filterable': True,
        'display_name': 'Face Name'
    },
    'side': {
        'type': 'string',
        'description': 'Side of the card (a, b)',
        'filterable': True,
        'display_name': 'Side'
    },

    # Mana and costs
    'mana_cost': {
        'type': 'string',
        'description': 'Mana cost in symbols',
        'filterable': True,
        'display_name': 'Mana Cost'
    },
    'mana_value': {
        'type': 'number',
        'description': 'Converted mana cost/mana value',
        'filterable': True,
        'display_name': 'Mana Value'
    },
    'face_mana_value': {
        'type': 'number',
        'description': 'Mana value for this face',
        'filterable': True,
        'display_name': 'Face Mana Value'
    },

    # Type information
    'type': {
        'type': 'string',
        'description': 'Full type line',
        'filterable': True,
        'display_name': 'Type'
    },
    'types': {
        'type': 'string_array',
        'description': 'Card types (Creature, Instant, etc.)',
        'filterable': True,
        'display_name': 'Types'
    },
    'subtypes': {
        'type': 'string_array',
        'description': 'Card subtypes (Goblin, Aura, etc.)',
        'filterable': True,
        'display_name': 'Subtypes'
    },
    'supertypes': {
        'type': 'string_array',
        'description': 'Card supertypes (Basic, Legendary, etc.)',
        'filterable': True,
        'display_name': 'Supertypes'
    },

    # Colors and color identity
    'colors': {
        'type': 'string_array',
        'description': 'Colors in mana cost',
        'filterable': True,
        'display_name': 'Colors'
    },
    'color_identity': {
        'type': 'string_array',
        'description': 'Colors in color identity',
        'filterable': True,
        'display_name': 'Color Identity'
    },

    # Gameplay characteristics
    'text': {
        'type': 'string',
        'description': 'Oracle card text',
        'filterable': True,
        'display_name': 'Text'
    },
    'keywords': {
        'type': 'string_array',
        'description': 'Keyword abilities',
        'filterable': True,
        'display_name': 'Keywords'
    },
    'power': {
        'type': 'string',  # Can include special values like *
        'description': 'Power (for creatures)',
        'filterable': True,
        'display_name': 'Power'
    },
    'toughness': {
        'type': 'string',  # Can include special values like *
        'description': 'Toughness (for creatures)',
        'filterable': True,
        'display_name': 'Toughness'
    },

    # Format legality
    'commander_legal': {
        'type': 'boolean',
        'description': 'Legal in Commander format',
        'filterable': True,
        'display_name': 'Commander Legal'
    },
    'modern_legal': {
        'type': 'boolean',
        'description': 'Legal in Modern format',
        'filterable': True,
        'display_name': 'Modern Legal'
    },
    'legacy_legal': {
        'type': 'boolean',
        'description': 'Legal in Legacy format',
        'filterable': True,
        'display_name': 'Legacy Legal'
    },
    'vintage_legal': {
        'type': 'boolean',
        'description': 'Legal in Vintage format',
        'filterable': True,
        'display_name': 'Vintage Legal'
    },
    'pioneer_legal': {
        'type': 'boolean',
        'description': 'Legal in Pioneer format',
        'filterable': True,
        'display_name': 'Pioneer Legal'
    },
    'brawl_legal': {
        'type': 'boolean',
        'description': 'Legal in Brawl format',
        'filterable': True,
        'display_name': 'Brawl Legal'
    },

    # Leadership capabilities
    'commander_eligible': {
        'type': 'boolean',
        'description': 'Can be a commander',
        'filterable': True,
        'display_name': 'Commander Eligible'
    },
    'oathbreaker_eligible': {
        'type': 'boolean',
        'description': 'Can be an oathbreaker',
        'filterable': True,
        'display_name': 'Oathbreaker Eligible'
    },
    'brawl_eligible': {
        'type': 'boolean',
        'description': 'Can be a brawl commander',
        'filterable': True,
        'display_name': 'Brawl Eligible'
    },

    # Rulings
    'has_rulings': {
        'type': 'boolean',
        'description': 'Has ruling entries',
        'filterable': True,
        'display_name': 'Has Rulings'
    },
    'ruling_count': {
        'type': 'number',
        'description': 'Number of rulings',
        'filterable': True,
        'display_name': 'Ruling Count'
    }
}

# ChromaDB filter operators for different data types
FILTER_OPERATORS = {
    'string': ['$eq', '$contains'],
    'string_array': ['$contains'],
    'number': ['$eq', '$gt', '$gte', '$lt', '$lte'],
    'boolean': ['$eq']
}

# Common color values in MTG
COLORS = ['White', 'Blue', 'Black', 'Red', 'Green']
COLOR_CODES = ['W', 'U', 'B', 'R', 'G']

# Common card types
CARD_TYPES = [
    'Creature', 'Instant', 'Sorcery', 'Artifact', 'Enchantment',
    'Land', 'Planeswalker', 'Battle'
]
