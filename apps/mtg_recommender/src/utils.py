import ast
import json
import requests
import pandas as pd
import streamlit as st
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
#from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from .constants import METADATA_FIELDS

# Constants for file paths and data locations
SCRIPT_DIR = Path(__file__).resolve().parent.parent
DATA_FOLDER = SCRIPT_DIR / "data"
CARDS_FILE = "AtomicCards.json"
RULES_FILE = "MagicCompRules_21031101.txt"
JSON_PATH = DATA_FOLDER / CARDS_FILE
TXT_PATH = DATA_FOLDER / RULES_FILE
PERSIST_PATH = DATA_FOLDER / "chroma_db"


def fetch_mtg_rules():
    """Download the latest MTG comprehensive rules and save locally."""
    url = "https://media.wizards.com/2025/downloads/MagicCompRules%2020250404.txt"
    print(f"Fetching rules from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    text = response.text
    TXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TXT_PATH, "w") as f:
        f.write(text)


def load_txt_file():
    """Load the MTG rules from file, or download if missing. Returns rules as a string."""
    if TXT_PATH.exists():
        with open(TXT_PATH, "r") as f:
            data = f.read()
        return data
    else:
        with st.spinner(f"{RULES_FILE} not found in {DATA_FOLDER}. Downloading..."):
            fetch_mtg_rules()
        return load_txt_file()


def fetch_mtgjson_data():
    """Download the latest MTG card data and save locally as JSON."""
    url = "https://mtgjson.com/api/v5/AtomicCards.json"
    print(f"Fetching data from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f)


def preprocess_card_fields(df):
    """Normalize card data fields and types according to METADATA_FIELDS."""
    # First convert all NaN values to None
    df = df.replace([pd.NA, pd.NaT, ''], None)
    df = df.where(pd.notna(df), None)
    
    # Process each field according to its type
    for col, field_info in METADATA_FIELDS.items():
        
        if col not in df.columns:
            df[col] = None
            continue
            
        field_type = field_info['type']
        if field_type == 'string_array':
            if col in ['rulings', 'foreignData']:
                df[col] = df[col].astype(str)
            else:
                # Convert lists to comma-separated strings, properly handling each array element
                df[col] = df[col].apply(lambda x: ', '.join(x) if isinstance(x, list) and x else None)
        elif field_type == 'boolean':
            # Convert nulls to False for boolean fields
            df[col] = df[col].fillna(False)
        elif field_type == 'number':
            # Ensure numbers are numeric, convert NaN to None
            df[col] = pd.to_numeric(df[col], errors='coerce').where(pd.notna(df[col]), None)
        # do nothing for strings
        elif col.startswith('legalities.'):
            df[col] = df[col].fillna('Not Legal')
    
    return df[list(METADATA_FIELDS.keys())]


def transform_card_data(data):
    """Convert raw MTG card data into a normalized pandas DataFrame."""
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
    """Load or fetch MTG card data and return as a normalized DataFrame."""
    if JSON_PATH.exists():
        with open(JSON_PATH, "r") as f:
            data = json.load(f)["data"]
        return transform_card_data(data)
    else:
        with st.spinner(f"{CARDS_FILE} not found in {DATA_FOLDER}. Downloading..."):
            fetch_mtgjson_data()
        return load_json_file()


def create_search_documents(df):
    """Convert card DataFrame rows into Langchain Document objects for vector storage."""
    docs = []
    for _, row in df.iterrows():
        # Create metadata dict using only fields defined in METADATA_FIELDS
        metadata = {
            col: val for col, val in row.items() 
            if col in METADATA_FIELDS
        }
        
        page_content = row['text'] if pd.notna(row['text']) else ''
        docs.append(Document(page_content=page_content, metadata=metadata))
    return docs


def build_vectorstore(df, persist_path=PERSIST_PATH, collection_name="mtg-poc", embedding_model="text-embedding-3-small", batch_size=500, show_progress=None):
    """Create or load a Chroma vector store from card data."""
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
                persist_directory=str(persist_path)
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
    """Get or create the Chroma vectorstore for card embeddings."""
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        show_progress_bar=False
    )
    
    # Check if vectorstore exists
    if PERSIST_PATH.exists():
        return Chroma(
            persist_directory=str(PERSIST_PATH),
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
