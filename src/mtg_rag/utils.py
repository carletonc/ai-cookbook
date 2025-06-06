import os
import json
import requests
import ast
import streamlit as st
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
#from langchain_community.vectorstores import Chroma
from langchain.schema import Document

# Constants for file paths and data locations
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = "data"
CARDS_FILE = "AtomicCards.json"
RULES_FILE = "MagicCompRules_21031101.txt"
JSON_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, CARDS_FILE)
TXT_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, RULES_FILE)
PERSIST_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, "chroma_db")


def fetch_mtgjson_data():
    """
    Fetch the latest MTG card data from MTGJSON and save it locally.
    
    Downloads the AtomicCards.json file which contains comprehensive data for all
    Magic: The Gathering cards, including card properties, rules text, and metadata.
    The file is saved to the configured data directory for local access.
    
    Raises:
        requests.exceptions.RequestException: If the download fails
        IOError: If there are issues writing the file
    """
    url = "https://mtgjson.com/api/v5/AtomicCards.json"
    print(f"Fetching data from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f)


def fetch_mtg_rules():
    """
    Fetch the official Magic: The Gathering comprehensive rules.
    
    Downloads the latest version of the comprehensive rules text file from
    Wizards of the Coast. This contains all game rules, mechanics explanations,
    and detailed gameplay procedures. The file is saved locally for reference
    and rules-based queries.
    
    Raises:
        requests.exceptions.RequestException: If the download fails
        IOError: If there are issues writing the file
    """
    url = "https://media.wizards.com/2025/downloads/MagicCompRules%2020250404.txt"
    print(f"Fetching rules from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    text = response.text
    os.makedirs(os.path.dirname(TXT_PATH), exist_ok=True)
    with open(TXT_PATH, "w") as f:
        f.write(text)


def get_json_file():
    """
    Load or fetch the MTG card data.
    
    Attempts to load the card data from the local JSON file. If the file doesn't
    exist, it downloads it first using fetch_mtgjson_data(). Shows a Streamlit
    progress indicator during download.
    
    Returns:
        dict: The complete MTG card database as a dictionary
    """
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r") as f:
            data = json.load(f)
        return data
    else:
        with st.spinner(f"{CARDS_FILE} not found in {DATA_FOLDER}. Downloading..."):
            fetch_mtgjson_data()
        return get_json_file()


def get_txt_file():
    """
    Load or fetch the MTG comprehensive rules.
    
    Attempts to load the rules from the local text file. If the file doesn't
    exist, it downloads it first using fetch_mtg_rules(). Shows a Streamlit
    progress indicator during download.
    
    Returns:
        str: The complete MTG comprehensive rules text
    """
    if os.path.exists(TXT_PATH):
        with open(TXT_PATH, "r") as f:
            data = f.read()
        return data
    else:
        with st.spinner(f"{RULES_FILE} not found in {DATA_FOLDER}. Downloading..."):
            fetch_mtg_rules()
        return get_txt_file()


def clean_card_dict(card_dict: dict) -> dict:
    """
    Clean and normalize card data for vector store ingestion.
    
    Processes a card dictionary from MTGJSON to:
    1. Remove unnecessary fields that don't contribute to search
    2. Preserve specific nested structures needed for metadata
    3. Convert remaining values to strings for vector store compatibility
    
    Args:
        card_dict (dict): Raw card dictionary from MTGJSON
        
    Returns:
        dict: Cleaned card dictionary with:
            - Extraneous fields removed
            - All simple values converted to strings
            - Preserved nested structures for metadata/rulings
            
    Note:
        Preserved keys include: identifiers, legalities, leadershipSkills, rulings
        Removed keys include: edhrecRank, edhrecSaltiness, foreignData, purchaseUrls, firstPrinting
    """
    remove_keys = {
        'edhrecRank', 'edhrecSaltiness', 'foreignData',
        'purchaseUrls', 'firstPrinting'
    }
    preserve_keys = {'identifiers', 'legalities', 'leadershipSkills', 'rulings'}
    cleaned = {}
    for k, v in card_dict.items():
        if k in remove_keys:
            continue
        if k in preserve_keys:
            cleaned[k] = v
        else:
            # Only convert to string if not already a string
            if isinstance(v, (dict, list)):
                cleaned[k] = v
            else:
                cleaned[k] = str(v)
    return cleaned


def flatten_card_data(card_data_dict):
    """
    Flatten the nested MTG card data structure into a list of individual card objects.
    
    The AtomicCards.json format groups cards by name, with each name potentially having
    multiple printings or variations. This function flattens that structure into a
    list where each entry is a complete card object.
    
    Args:
        card_data_dict (dict): The 'data' dict from AtomicCards.json, keyed by card name
        
    Returns:
        list[dict]: A list of card dictionaries, each representing a unique printing
            or variation of a card with consistent naming and cleaned data
            
    Example:
        Input format:
        {
            "Lightning Bolt": [
                {version1 data},
                {version2 data}
            ],
            ...
        }
        
        Output format:
        [
            {"name": "Lightning Bolt", ...version1 data},
            {"name": "Lightning Bolt", ...version2 data},
            ...
        ]
    """
    flat_cards = []
    for name, cards in card_data_dict.items():
        card_list = ast.literal_eval(cards) if isinstance(cards, str) else cards
        for card in card_list:
            cleaned = clean_card_dict(card)
            cleaned['name'] = name  # Ensure consistent naming
            flat_cards.append(cleaned)
    return flat_cards


def create_comprehensive_metadata(card):
    """
    Create a rich metadata dictionary for a card to enable advanced filtering and context.
    
    Extracts and organizes card attributes into a structured metadata dictionary that
    supports complex filtering operations in the vector store. This includes both
    core card attributes and derived fields useful for search and filtering.
    
    Args:
        card (dict): A cleaned card dictionary containing all card attributes
        
    Returns:
        dict: A metadata dictionary with organized fields including:
            - Core identification (name, oracle_id, layout)
            - Mana and color information
            - Card type data
            - Game mechanics (keywords, abilities)
            - Format legality
            - Commander-specific attributes
            - Set and rarity information
            
    Note:
        The metadata structure is designed to support both exact and fuzzy matching
        in ChromaDB queries, with string representations of complex fields to
        enable text-based filtering.
    """
    metadata = {
        # Core identification
        'name': card.get('name'),
        'oracle_id': card.get('identifiers', {}).get('scryfallOracleId'),
        'layout': card.get('layout'),
        'face_name': card.get('faceName'),
        'side': card.get('side'),
        
        # Face-specific mana information
        'face_converted_mana_cost': card.get('faceConvertedManaCost'),
        'face_mana_value': card.get('faceManaValue'),
        
        # Game mechanics
        'type': card.get('type'),
        'types': ','.join(card.get('types', [])),
        'subtypes': ','.join(card.get('subtypes', [])),
        'supertypes': ','.join(card.get('supertypes', [])),
        'mana_cost': card.get('manaCost'),
        'mana_value': card.get('manaValue'),
        'converted_mana_cost': card.get('convertedManaCost'),
        'colors': ','.join(card.get('colors', [])),
        'color_identity': ','.join(card.get('colorIdentity', [])),
        'keywords': ','.join(card.get('keywords', [])),
        'text': card.get('text'), 
        
        # Creature-specific
        'power': card.get('power'),
        'toughness': card.get('toughness'),
        
        # Format legalities
        'commander_legal': card.get('legalities', {}).get('commander') == 'Legal', 
        'modern_legal': card.get('legalities', {}).get('modern') == 'Legal', 
        'legacy_legal': card.get('legalities', {}).get('legacy') == 'Legal', 
        'vintage_legal': card.get('legalities', {}).get('vintage') == 'Legal', 
        'brawl_legal': card.get('legalities', {}).get('brawl') == 'Legal', 
        'pioneer_legal': card.get('legalities', {}).get('pioneer') == 'Legal', 
        
        # Leadership capabilities
        'commander_eligible': card.get('leadershipSkills', {}).get('commander', False), 
        'oathbreaker_eligible': card.get('leadershipSkills', {}).get('oathbreaker', False), 
        'brawl_eligible': card.get('leadershipSkills', {}).get('brawl', False), 
        
        # Rulings summary for filtering
        'has_rulings': len(card.get('rulings', [])) > 0, 
        'ruling_count': len(card.get('rulings', [])), 
    }
    
    # Remove None values and empty strings
    return {k: v for k, v in metadata.items() if v is not None and v != ''}


def create_rich_page_content(card):
    """
    Generate comprehensive searchable content for a card including rules text and rulings.
    
    Creates a structured text representation of a card that includes all relevant
    information for semantic search, including card properties, rules text, and
    recent rulings. The content is formatted in a way that enhances natural
    language queries.
    
    Args:
        card (dict): A cleaned card dictionary containing all card attributes
        
    Returns:
        str: A newline-separated string containing formatted card information with sections:
            - Basic card information (name, type, mana cost)
            - Face-specific information for double-faced cards
            - Power/Toughness for creatures
            - Color information
            - Commander format information
            - Card text
            - Recent rulings (up to 5, sorted by date)
            
    Note:
        The content is structured to support natural language queries while
        maintaining important game-specific terminology for accurate matching.
    """
    content_parts = []

    # Card name (always include)
    #if card.get('name'):
    #    content_parts.append(f"Name: {card.get('name')}")

    # Type line
    if card.get('type'):
        content_parts.append(f"Type: {card.get('type')}")

    # Mana cost
    if card.get('manaCost'):
        content_parts.append(f"Mana Cost: {card.get('manaCost')}")

    # Face name for double-faced cards
    if card.get('faceName'):
        content_parts.append(f"Face: {card.get('faceName')}")

    # Face-specific mana cost for DFCs
    if card.get('faceConvertedManaCost') and card.get('faceConvertedManaCost') != card.get('convertedManaCost'):
        content_parts.append(f"Face Mana Value: {card.get('faceConvertedManaCost')}")

    # Power/Toughness for creatures
    if card.get('power') and card.get('toughness'):
        content_parts.append(f"Power/Toughness: {card.get('power')}/{card.get('toughness')}")

    # Colors and color identity
    if card.get('colors'):
        if isinstance(card.get('colors'), list):
            colors = ', '.join(card.get('colors'))
        else:
            colors = str(card.get('colors'))
        content_parts.append(f"Colors: {colors}")
    if card.get('colorIdentity'):
        if isinstance(card.get('colorIdentity'), list):
            color_identity = ', '.join(card.get('colorIdentity'))
        else:
            color_identity = str(card.get('colorIdentity'))
        content_parts.append(f"Color Identity: {color_identity}")

    # Commander legal and eligible
    commander_legal = card.get('legalities', {}).get('commander') == 'Legal'
    if commander_legal:
        content_parts.append("Commander Legal: Yes")
    else:
        content_parts.append("Commander Legal: No")
    commander_eligible = card.get('leadershipSkills', {}).get('commander', False)
    if commander_eligible:
        content_parts.append("Commander Eligible: Yes")
    else:
        content_parts.append("Commander Eligible: No")

    # Main card text (oracle text)
    card_text = card.get('text') or card.get('oracleText')
    if card_text:
        content_parts.append(f"Card Text: {card_text}")

    # Include recent rulings for complex cards (limit to most recent 5)
    rulings = card.get('rulings', [])
    if isinstance(rulings, list) and rulings:
        sorted_rulings = sorted(rulings, key=lambda x: x.get('date', ''), reverse=True)[:5]
        for ruling in sorted_rulings:
            content_parts.append(f"Ruling ({ruling.get('date', 'Unknown')}): {ruling.get('text', '')}")

    return '\n'.join(content_parts)


def create_search_documents(flat_cards):
    """
    Convert processed card data into Langchain Document objects for vector storage.
    
    Creates Document objects with rich page content and comprehensive metadata
    for each card, preparing them for ingestion into a vector store. The page
    content is optimized for semantic search while the metadata enables
    precise filtering.
    
    Args:
        flat_cards (list[dict]): List of processed card dictionaries from flatten_card_data()
        
    Returns:
        list[Document]: List of Langchain Document objects, each containing:
            - page_content: Rich text representation from create_rich_page_content()
            - metadata: Comprehensive metadata from create_comprehensive_metadata()
            
    Note:
        The resulting documents are ready for direct ingestion into ChromaDB
        or other vector stores that support the Langchain Document format.
    """
    docs = []
    for card in flat_cards:
        page_content = create_rich_page_content(card)
        metadata = create_comprehensive_metadata(card)
        docs.append(Document(
            page_content=page_content,
            metadata=metadata
        ))
    return docs


def get_mtg_vectorstore(card_data_dict, persist_path=PERSIST_PATH, collection_name="mtg-poc", embedding_model="text-embedding-3-small", batch_size=500, show_progress=None):
    """
    Initialize or load a ChromaDB vector store for MTG card search.
    
    Sets up a persistent vector store for card data using ChromaDB and OpenAI embeddings.
    If the collection exists, it's loaded from disk. If empty or non-existent,
    it's populated with card data. The store supports both semantic search and
    metadata filtering.
    
    Args:
        card_data_dict (dict): Raw card data dictionary from AtomicCards.json
        persist_path (str, optional): Path to store the ChromaDB files. Defaults to PERSIST_PATH.
        collection_name (str, optional): Name of the ChromaDB collection. Defaults to "mtg-poc".
        embedding_model (str, optional): OpenAI embedding model to use. Defaults to "text-embedding-3-small".
        batch_size (int, optional): Size of batches for vector store ingestion. Defaults to 500.
        show_progress (function, optional): Callback for progress updates. Defaults to None.
        
    Returns:
        Chroma: Initialized ChromaDB vector store instance
        
    Note:
        The function handles directory permissions and ensures the persist directory
        is properly set up. It uses batched ingestion to handle large card datasets
        efficiently.
    """
    # Ensure the persist_path directory exists and is writable
    persist_dir = os.path.abspath(persist_path)
    if not os.path.exists(persist_dir):
        os.makedirs(persist_dir, exist_ok=True)
        os.chmod(persist_dir, 0o755)
    else:
        try:
            os.chmod(persist_dir, 0o755)
        except Exception as e:
            print(f"Warning: Could not set permissions on {persist_dir}: {e}")

    embedding = OpenAIEmbeddings(model=embedding_model)
    # Always create the Chroma instance first
    vectorstore = Chroma(
        persist_directory=persist_path,
        collection_name=collection_name,
        embedding_function=embedding
    )

    # Check if the collection already has documents
    try:
        doc_count = vectorstore._collection.count()
    except Exception:
        doc_count = 0

    if doc_count == 0:
        flat_cards = flatten_card_data(card_data_dict)
        docs = create_search_documents(flat_cards)
        print("Flat cards:", len(flat_cards))
        print("Docs:", len(docs))
        print("Persist path exists:", os.path.exists(persist_path))
        print("Persist path is dir:", os.path.isdir(persist_path))

        def batch(iterable, size=batch_size):
            for i in range(0, len(iterable), size):
                yield iterable[i:i + size]

        total = len(docs)
        for i, doc_chunk in enumerate(batch(docs, size=batch_size)):
            vectorstore.add_documents(doc_chunk)
            if show_progress:
                show_progress(min((i+1)*batch_size/total, 1.0))
        #vectorstore.persist()
    return vectorstore