
import json
import requests
import pandas as pd
import streamlit as st

from pathlib import Path

from src.constants import METADATA_FIELDS

# Constants for file paths and data locations
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FOLDER = SCRIPT_DIR / "data"
CARDS_FILE = "AtomicCards.json"
RULES_FILE = "MagicCompRules_21031101.txt"
JSON_PATH = DATA_FOLDER / CARDS_FILE
TXT_PATH = DATA_FOLDER / RULES_FILE



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
            
        # handle strings specifically or do nothing 
        elif col.startswith('legalities.'):
            df[col] = df[col].fillna('Not Legal')
        elif col == 'faceName':
            locs = df[col].isna()
            df.loc[locs, 'faceName'] = df.loc[locs, 'name']
        
    
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