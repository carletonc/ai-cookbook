import ast
import os
import json
import requests
import pandas as pd
import streamlit as st
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
#from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from constants import METADATA_FIELDS

# Constants for file paths and data locations
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = "data"
CARDS_FILE = "AtomicCards.json"
RULES_FILE = "MagicCompRules_21031101.txt"
JSON_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, CARDS_FILE)
TXT_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, RULES_FILE)
PERSIST_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, "chroma_db")


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


def load_txt_file():
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
        return load_txt_file()


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


def preprocess_card_fields(df):
    """
    Normalize card data fields according to their types in METADATA_FIELDS.
    Handles null values and ensures all required columns exist.
    
    Args:
        df (pd.DataFrame): Raw card DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with normalized fields and proper types
    """
    # First convert all NaN values to None
    df = df.replace([pd.NA, pd.NaT, ''], None)
    df = df.where(pd.notna(df), None)
    
    # Process each field according to its type
    for col, field_info in METADATA_FIELDS.items():
        print(col)
        if col not in df.columns:
            df[col] = None
            continue
            
        field_type = field_info['type']
        if field_type == 'string_array':
            if col in ['rulings', 'foreignData']:
                df[col] = df[col].astype(str)
            else:
                # Convert lists to comma-separated strings, properly handling each array element
                df[col] = df[col].apply(lambda x: ','.join(x) if isinstance(x, list) and x else None)
        elif field_type == 'boolean':
            # Convert nulls to False for boolean fields
            df[col] = df[col].fillna(False)
        elif field_type == 'number':
            # Ensure numbers are numeric, convert NaN to None
            df[col] = pd.to_numeric(df[col], errors='coerce').where(pd.notna(df[col]), None)
    
    return df[list(METADATA_FIELDS.keys())]


def transform_card_data(data):
    """
    Transform raw MTG card data into a normalized pandas DataFrame.
    
    Args:
        data (dict): Raw card data from MTGJSON
        
    Returns:
        pandas.DataFrame: Normalized DataFrame with proper types and null handling
    """
    # Convert nested card data into a flat DataFrame
    df = pd.json_normalize(data)
    # Expand card variants into separate rows
    df = df.transpose().explode(0).reset_index().rename(columns={'index': 'cardName'})
    # Normalize the card data into columns
    df = pd.concat([
        df['cardName'], 
        pd.json_normalize(df[0]) 
    ], axis=1) 
    
    # Reorder columns to match output_cols
    return preprocess_card_fields(df) 


def load_json_file():
    """
    Load or fetch the MTG card data and transform it into a pandas DataFrame.
    
    Attempts to load the card data from the local JSON file. If the file doesn't
    exist, it downloads it first using fetch_mtgjson_data().
    
    Returns:
        pandas.DataFrame: Flattened and normalized card data with columns matching output_cols
    """
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r") as f:
            data = json.load(f)["data"]
        return transform_card_data(data)
    else:
        with st.spinner(f"{CARDS_FILE} not found in {DATA_FOLDER}. Downloading..."):
            fetch_mtgjson_data()
        return load_json_file()


def create_rich_page_content(card_row):
    """
    Extract semantic search content from a card row. Currently focused on rules text only
    as the primary vector for semantic search, with other card attributes available as 
    metadata filters.
    
    This function is designed to be extensible - we can add more content types to the
    semantic search later (e.g., flavor text, card names for similar card searches) while
    keeping the initial implementation focused on rules interactions.
    
    Args:
        card_row (pandas.Series): A row from the card DataFrame containing preprocessed data
        
    Returns:
        str: Currently just the card's rules text, or empty string if no rules text.
             The return type will remain str even as we extend the function.
    """
    output = card_row['text'] if pd.notna(card_row['text']) else ''
    return output


def create_search_documents(df):
    """
    Convert processed card data into Langchain Document objects for vector storage.
    
    Ensures metadata is properly formatted for ChromaDB:
    - Arrays are stored as Python lists for proper $contains, $all operations
    - Numbers are stored as floats for proper numeric comparisons
    - Booleans are stored as Python booleans
    - Strings are stored as clean, normalized strings
    
    Args:
        df (pandas.DataFrame): DataFrame containing processed card data
        
    Returns:
        list[Document]: List of Langchain Document objects ready for vector store ingestion
    """
    docs = []
    for _, row in df.iterrows():
        # Create metadata dict using only fields defined in METADATA_FIELDS
        metadata = {
            col: val for col, val in row.items() 
            if col in METADATA_FIELDS
        }
        
        page_content = create_rich_page_content(row)
        docs.append(Document(page_content=page_content, metadata=metadata))
    return docs


def build_vectorstore(df, persist_path=PERSIST_PATH, collection_name="mtg-poc", embedding_model="text-embedding-3-small", batch_size=500, show_progress=None):
    """
    Create or load a Chroma vector store from the processed card data.
    
    Args:
        df (pandas.DataFrame): DataFrame containing the card data
        persist_path (str): Path to persist the vector store
        collection_name (str): Name for the Chroma collection
        embedding_model (str): OpenAI embedding model to use
        batch_size (int): Number of documents to process at once
        show_progress (callable, optional): Function to call with progress updates
        
    Returns:
        Chroma: Configured vector store with card documents and metadata
    """
    embeddings = OpenAIEmbeddings(
        model=embedding_model,
        show_progress_bar=False
    )
    
    # Create document objects
    documents = create_search_documents(df)
    total_docs = len(documents)
    
    if show_progress:
        show_progress(0)
    
    # Process in batches
    vectorstore = None
    for i in range(0, total_docs, batch_size):
        batch = documents[i:i+batch_size]
        
        if vectorstore is None:
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                collection_name=collection_name,
                persist_directory=persist_path
            )
        else:
            vectorstore.add_documents(batch)
        
        if show_progress:
            progress = min((i + batch_size) / total_docs, 1.0)
            show_progress(progress)
    
    if show_progress:
        show_progress(1.0)
    
    return vectorstore


def get_vector_store():
    """
    Get or create the Chroma vectorstore for card embeddings.
    
    If a vectorstore already exists at PERSIST_PATH, loads and returns it.
    Otherwise, builds a new vectorstore from the card data with progress feedback.
    
    Returns:
        Chroma: The vectorstore containing card embeddings
    """
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        show_progress_bar=False
    )
    
    # Check if vectorstore exists
    if os.path.exists(PERSIST_PATH):
        return Chroma(
            persist_directory=PERSIST_PATH,
            embedding_function=embeddings,
            collection_name="mtg-poc"
        )
    
    # If not, build it from scratch
    rules = load_txt_file()
    card_df = load_json_file()
    
    # Use Streamlit progress bar for feedback
    progress_text = st.empty()
    progress_text.text("Building Chroma vectorstore...")
    progress_bar = st.progress(0)
    
    def show_progress(val):
        progress_bar.progress(val)
        
    vectorstore = build_vectorstore(
        card_df, 
        persist_path=PERSIST_PATH, 
        collection_name="mtg-poc", 
        embedding_model="text-embedding-3-small", 
        batch_size=500, 
        show_progress=show_progress 
    )
    
    # Hide progress bar after vectorstore creation
    progress_bar.empty()
    progress_text.empty()
    
    return vectorstore