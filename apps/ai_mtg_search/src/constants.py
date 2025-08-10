# Metadata field definitions for MTG cards.
# Each field includes its type, description, filterability, and display name for UI.
METADATA_FIELDS = {
    # Core identification
    'cardName': {
        'type': 'string',
        'description': 'Card name.',
        'filterable': True,
        'display_name': 'Card Name'
    },
    'identifiers.scryfallOracleId': {
        'type': 'string',
        'description': 'Unique Scryfall Oracle ID.',
        'filterable': False,
        'display_name': 'Oracle ID'
    },
    'colorIdentity': {
        'type': 'string_array',
        'description': 'List of all colors found in manaCost, colorIndicator, and text.',
        'filterable': True,
        'display_name': 'Color Identity'
    },
    'colors': {
        'type': 'string_array',
        'description': 'List of all colors in manaCost and colorIndicator. Cards with Devoid have no color.',
        'filterable': True,
        'display_name': 'Colors'
    },
    'manaCost': {
        'type': 'string',
        'description': 'Mana cost in symbols (normal or split cards).',
        'filterable': True,
        'display_name': 'Mana Cost'
    },
    'convertedManaCost': {
        'type': 'number',
        'description': 'Converted mana cost (same as manaValue).',
        'filterable': True,
        'display_name': 'Converted Mana Cost'
    },
    'manaValue': {
        'type': 'number',
        'description': 'Mana value (same as convertedManaCost).',
        'filterable': True,
        'display_name': 'Mana Value'
    },
    
    # SIDE-SPECIFIC VALUES
    'layout': {
        'type': 'string',
        'description': 'Card layout type (normal, split, flip, etc.).',
        'filterable': True,
        'display_name': 'Layout'
    },
    'side': {
        'type': 'string',
        'description': 'Side of the card (a, b).',
        'filterable': True,
        'display_name': 'Side'
    },
    'faceName': {
        'type': 'string',
        'description': 'Name of this face (for multi-faced cards).',
        'filterable': True,
        'display_name': 'Face Name'
    },
    'faceConvertedManaCost': {
        'type': 'number',
        'description': 'Mana value for this face (same as faceManaValue).',
        'filterable': True,
        'display_name': 'Face Converted Mana Cost'
    },
    'faceManaValue': {
        'type': 'number',
        'description': 'Mana value for this face (same as faceConvertedManaCost).',
        'filterable': True,
        'display_name': 'Face Mana Value'
    },
    'colorIndicator': {
        'type': 'string_array',
        'description': 'Colors indicated on the card, relevant for transform cards.',
        'filterable': True,
        'display_name': 'Color Indicator'
    },
    
    # TEXT
    'keywords': {
        'type': 'string_array',
        'description': 'Keyword abilities.',
        'filterable': True,
        'display_name': 'Keywords'
    },
    'text': {
        'type': 'string',
        'description': 'Oracle card text.',
        'filterable': True,
        'display_name': 'Text'
    },
    'rulings': {
        'type': 'string_array',
        'description': 'Card rulings.',
        'filterable': False,
        'display_name': 'Rulings'
    },
    
    # SPECIFIC TO CARD TYPES
    'power': {
        'type': 'string',
        'description': 'Power (for creatures).',
        'filterable': True,
        'display_name': 'Power'
    },
    'toughness': {
        'type': 'string',
        'description': 'Toughness (for creatures).',
        'filterable': True,
        'display_name': 'Toughness'
    },
    'loyalty': {
        'type': 'string',
        'description': 'Loyalty (for planeswalkers).',
        'filterable': True,
        'display_name': 'Loyalty'
    },
    'defense': {
        'type': 'string',
        'description': 'Defense (for battles).',
        'filterable': True,
        'display_name': 'Defense'
    },
    'hasAlternativeDeckLimit': {
        'type': 'boolean',
        'description': 'Allows more than 4 copies in a deck.',
        'filterable': True,
        'display_name': 'Has Alternative Deck Limit'
    },
    
    # TYPES
    'type': {
        'type': 'string',
        'description': 'Full type line.',
        'filterable': True,
        'display_name': 'Type'
    },
    'types': {
        'type': 'string_array',
        'description': 'Card types (Creature, Instant, etc.).',
        'filterable': True,
        'display_name': 'Types'
    },
    'subtypes': {
        'type': 'string_array',
        'description': 'Card subtypes (Goblin, Aura, etc.).',
        'filterable': True,
        'display_name': 'Subtypes'
    },
    'supertypes': {
        'type': 'string_array',
        'description': 'Card supertypes (Basic, Legendary, etc.).',
        'filterable': True,
        'display_name': 'Supertypes'
    },
    
    # LEADERSHIP
    'leadershipSkills.brawl': {
        'type': 'boolean',
        'description': 'Can be a brawl commander.',
        'filterable': True,
        'display_name': 'Brawl Commander Eligible'
    },
    'leadershipSkills.commander': {
        'type': 'boolean',
        'description': 'Can be a commander.',
        'filterable': True,
        'display_name': 'Commander Eligible'
    },
    'leadershipSkills.oathbreaker': {
        'type': 'boolean',
        'description': 'Can be an oathbreaker.',
        'filterable': True,
        'display_name': 'Oathbreaker Eligible'
    },
    
    # LEGALITIES
    'legalities.alchemy': {
        'type': 'string',
        'description': 'Legality in Alchemy format.',
        'filterable': True,
        'display_name': 'Alchemy Legal'
    },
    'legalities.brawl': {
        'type': 'string',
        'description': 'Legality in Brawl format.',
        'filterable': True,
        'display_name': 'Brawl Legal'
    },
    'legalities.commander': {
        'type': 'string',
        'description': 'Legality in Commander format.',
        'filterable': True,
        'display_name': 'Commander Legal'
    },
    'legalities.duel': {
        'type': 'string',
        'description': 'Legality in Duel Commander format.',
        'filterable': True,
        'display_name': 'Duel Commander Legal'
    },
    'legalities.explorer': {
        'type': 'string',
        'description': 'Legality in Explorer format.',
        'filterable': True,
        'display_name': 'Explorer Legal'
    },
    'legalities.future': {
        'type': 'string',
        'description': 'Legality in Future format.',
        'filterable': True,
        'display_name': 'Future Legal'
    },
    'legalities.gladiator': {
        'type': 'string',
        'description': 'Legality in Gladiator format.',
        'filterable': True,
        'display_name': 'Gladiator Legal'
    },
    'legalities.historic': {
        'type': 'string',
        'description': 'Legality in Historic format.',
        'filterable': True,
        'display_name': 'Historic Legal'
    },
    'legalities.legacy': {
        'type': 'string',
        'description': 'Legality in Legacy format.',
        'filterable': True,
        'display_name': 'Legacy Legal'
    },
    'legalities.modern': {
        'type': 'string',
        'description': 'Legality in Modern format.',
        'filterable': True,
        'display_name': 'Modern Legal'
    },
    'legalities.oathbreaker': {
        'type': 'string',
        'description': 'Legality in Oathbreaker format.',
        'filterable': True,
        'display_name': 'Oathbreaker Legal'
    },
    'legalities.oldschool': {
        'type': 'string',
        'description': 'Legality in Old School format.',
        'filterable': True,
        'display_name': 'Old School Legal'
    },
    'legalities.pauper': {
        'type': 'string',
        'description': 'Legality in Pauper format.',
        'filterable': True,
        'display_name': 'Pauper Legal'
    },
    'legalities.paupercommander': {
        'type': 'string',
        'description': 'Legality in Pauper Commander format.',
        'filterable': True,
        'display_name': 'Pauper Commander Legal'
    },
    'legalities.penny': {
        'type': 'string',
        'description': 'Legality in Penny Dreadful format.',
        'filterable': True,
        'display_name': 'Penny Dreadful Legal'
    },
    'legalities.pioneer': {
        'type': 'string',
        'description': 'Legality in Pioneer format.',
        'filterable': True,
        'display_name': 'Pioneer Legal'
    },
    'legalities.predh': {
        'type': 'string',
        'description': 'Legality in Pre-EDH format.',
        'filterable': True,
        'display_name': 'Pre-EDH Legal'
    },
    'legalities.premodern': {
        'type': 'string',
        'description': 'Legality in Premodern format.',
        'filterable': True,
        'display_name': 'Premodern Legal'
    },
    'legalities.standard': {
        'type': 'string',
        'description': 'Legality in Standard format.',
        'filterable': True,
        'display_name': 'Standard Legal'
    },
    'legalities.standardbrawl': {
        'type': 'string',
        'description': 'Legality in Standard Brawl format.',
        'filterable': True,
        'display_name': 'Standard Brawl Legal'
    },
    'legalities.timeless': {
        'type': 'string',
        'description': 'Legality in Timeless format.',
        'filterable': True,
        'display_name': 'Timeless Legal'
    },
    'legalities.vintage': {
        'type': 'string',
        'description': 'Legality in Vintage format.',
        'filterable': True,
        'display_name': 'Vintage Legal'
    },
    
    # PURCHASE URLS
    'purchaseUrls.cardKingdom': {
        'type': 'string',
        'description': 'Card Kingdom purchase URL.',
        'filterable': False,
        'display_name': 'Card Kingdom URL'
    },
    'purchaseUrls.cardKingdomEtched': {
        'type': 'string',
        'description': 'Card Kingdom etched foil purchase URL.',
        'filterable': False,
        'display_name': 'Card Kingdom Etched URL'
    },
    'purchaseUrls.cardKingdomFoil': {
        'type': 'string',
        'description': 'Card Kingdom foil purchase URL.',
        'filterable': False,
        'display_name': 'Card Kingdom Foil URL'
    },
    'purchaseUrls.cardmarket': {
        'type': 'string',
        'description': 'Cardmarket purchase URL.',
        'filterable': False,
        'display_name': 'Cardmarket URL'
    },
    'purchaseUrls.tcgplayer': {
        'type': 'string',
        'description': 'TCGPlayer purchase URL.',
        'filterable': False,
        'display_name': 'TCGPlayer URL'
    },
    'purchaseUrls.tcgplayerEtched': {
        'type': 'string',
        'description': 'TCGPlayer etched foil purchase URL.',
        'filterable': False,
        'display_name': 'TCGPlayer Etched URL'
    },
    
    # EDHREC, DOESNT MATTER
    'edhrecRank': {
        'type': 'number',
        'description': 'Rank on EDHREC.',
        'filterable': False,
        'display_name': 'EDHREC Rank'
    },
    'edhrecSaltiness': {
        'type': 'number',
        'description': 'Saltiness score on EDHREC.',
        'filterable': False,
        'display_name': 'EDHREC Saltiness'
    },
    
    # PRINTINGS AND WHATEVER
    'firstPrinting': {
        'type': 'string',
        'description': 'First printing of the card.',
        'filterable': False,
        'display_name': 'First Printing'
    },
    'printings': {
        'type': 'string_array',
        'description': 'All printings of the card.',
        'filterable': False,
        'display_name': 'Printings'
    },
    'foreignData': {
        'type': 'string_array',
        'description': 'Foreign language versions.',
        'filterable': False,
        'display_name': 'Foreign Data'
    },
    
    # WHO CARES FIX LATER
    'hand': {
        'type': 'string',
        'description': 'Hand modifier for Vanguard cards.',
        'filterable': False,
        'display_name': 'Hand Modifier'
    },
    'isFunny': {
        'type': 'boolean',
        'description': 'Whether the card is from a joke set.',
        'filterable': False,
        'display_name': 'Is Funny'
    },
    'isReserved': {
        'type': 'boolean',
        'description': 'Whether the card is on the Reserved List.',
        'filterable': False,
        'display_name': 'Is Reserved'
    },
    'life': {
        'type': 'string',
        'description': 'Life modifier for Vanguard cards.',
        'filterable': False,
        'display_name': 'Life Modifier'
    },
    
    # IGNORE
    'asciiName': {
        'type': 'string',
        'description': 'ASCII version of the card name.',
        'filterable': False,
        'display_name': 'ASCII Name'
    },
    'name': {
        'type': 'string',
        'description': 'Card name (duplicate of cardName).',
        'filterable': False,
        'display_name': 'Name'
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
COLOR_MAP = {
    'W':'White', 
    'U':'Blue', 
    'B':'Black', 
    'R':'Red', 
    'G':'Green'
}

# Common card types
CARD_TYPES = [
    'Creature', 'Instant', 'Sorcery', 'Artifact', 'Enchantment',
    'Land', 'Planeswalker', 'Battle', 
    # 'Kindred', 'Plane', 'Vanguard', 'Scheme', 'Stickers', 'Phenomenon', 'Conspiracy', 'Dungeon'
]