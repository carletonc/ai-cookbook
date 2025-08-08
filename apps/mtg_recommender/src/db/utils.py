import json
import os
import requests
import pandas as pd
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

from ..constants import METADATA_FIELDS

# Constants for file paths and data locations
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FOLDER = SCRIPT_DIR / "data"
CARDS_FILE = "AtomicCards.json"
RULES_FILE = "MagicCompRules_21031101.txt"
JSON_PATH = DATA_FOLDER / CARDS_FILE
TXT_PATH = DATA_FOLDER / RULES_FILE
PERSIST_PATH = DATA_FOLDER / "chroma_db"

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "mtg-cards"
PINECONE_ENVIRONMENT = "us-east-1-aws"  # Update with your preferred environment
EMBEDDING_MODEL = "text-embedding-3-small"
DIMENSION = 1536  # Dimension for text-embedding-3-small



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
                df[col] = df[col].apply(lambda x: ','.join(x) if isinstance(x, list) and x else None)
        elif field_type == 'boolean':
            # Convert nulls to False for boolean fields
            df[col] = df[col].fillna(False)
        elif field_type == 'number':
            # Ensure numbers are numeric, convert NaN to None
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(object)
            df[col] = df[col].where(df[col].notna(), None)
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
            # Pinecone requires metadata if it is present, 
            # `val is not None` is to avoid empty strings/fields
            if col in METADATA_FIELDS and val is not None 
        }
        
        page_content = row['text'] if pd.notna(row['text']) else ''
        docs.append(Document(page_content=page_content, metadata=metadata))
    return docs


def initialize_pinecone():
    """Initialize Pinecone client and create index if it doesn't exist."""
    pc = Pinecone(api_key=PINECONE_API_KEY)
    
    # Check if index exists, create if it doesn't
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=PINECONE_ENVIRONMENT
            )
        )
    return pc


def build_vectorstore(df, index_name=PINECONE_INDEX_NAME, batch_size=500, show_progress=None):
    """Create or load a Pinecone vector store from card data."""
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        show_progress_bar=False
    )
    
    # Initialize Pinecone
    pc = initialize_pinecone()
    
    # Create document objects
    documents = create_search_documents(df)
    total_docs = len(documents)
    
    if show_progress:
        show_progress(0)
    
    # Process in batches to show progress
    vectorstore = None
    for i in range(0, total_docs, batch_size):
        batch = documents[i:i+batch_size]
        
        if vectorstore is None:
            vectorstore = PineconeVectorStore.from_documents(
                documents=batch,
                embedding=embeddings,
                index_name=index_name
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
    """Get or create the Pinecone vectorstore for card embeddings."""
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        show_progress_bar=False
    )
    
    # Initialize Pinecone
    pc = initialize_pinecone()
    index = pc.Index(PINECONE_INDEX_NAME)
    
    # Check if index has vectors
    try:
        index_stats = index.describe_index_stats()
        if index_stats['total_vector_count'] > 0:
            # Index exists and has data, return existing vectorstore
            return PineconeVectorStore(
                index=index,
                embedding=embeddings
            )
    except Exception:
        pass  # Index might not exist yet
    
    # If index is empty, build it from scratch
    rules = load_txt_file()
    card_df = load_json_file()
    
    # Use Streamlit progress bar for feedback
    progress_text = st.empty()
    progress_text.text("Building vectorstore...")
    progress_bar = st.progress(0)
    
    def show_progress(val):
        progress_bar.progress(val)
        
    vectorstore = build_vectorstore(
        card_df, 
        index_name=PINECONE_INDEX_NAME,
        batch_size=500, 
        show_progress=show_progress 
    )
    
    # Hide progress bar after vectorstore creation
    progress_bar.empty()
    progress_text.empty()
    
    return vectorstore


# Alternative function if you want to clear/reset the index
def reset_vector_store(index_name=PINECONE_INDEX_NAME):
    """Delete and recreate the Pinecone index."""
    pc = Pinecone(api_key=PINECONE_API_KEY)
    
    # Delete existing index
    if index_name in pc.list_indexes().names():
        pc.delete_index(index_name)
    
    # Recreate index
    pc.create_index(
        name=index_name,
        dimension=DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region=PINECONE_ENVIRONMENT
        )
    )