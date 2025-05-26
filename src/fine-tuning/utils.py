import os
import json
import requests
import streamlit as st

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = "data"
CARDS_FILE = "AtomicCards.json"
RULES_FILE = "MagicCompRules_21031101.txt"
JSON_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, CARDS_FILE)
TXT_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, RULES_FILE)

def fetch_mtgjson_data():
    """Fetch data from MTGJSON and return as DataFrame"""
    url = "https://mtgjson.com/api/v5/AtomicCards.json"
    print(f"Fetching data from {url}...")
    
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    # Save to file
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f)
    return 

def fetch_mtg_rules():
    """Fetch Magic Comp Rules from MTGJSON and return as text"""
    url = "https://media.wizards.com/2025/downloads/MagicCompRules%2020250404.txt"
    print(f"Fetching rules from {url}...")
    
    response = requests.get(url)
    response.raise_for_status()
    text = response.text
    # Save to file
    os.makedirs(os.path.dirname(TXT_PATH), exist_ok=True)
    with open(TXT_PATH, "w") as f:
        f.write(text)
    return 

def get_json_file():
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r") as f:
            data = json.load(f)
        return data
    else:
        st.warning(f"{CARDS_FILE} not found in {DATA_FOLDER}.")
        download_json_file()  # Placeholder: implement this function to download the file
        return get_json_file()  # Retry after download

def get_txt_file():
    if os.path.exists(TXT_PATH):
        with open(TXT_PATH, "r") as f:
            data = f.read()
        return data
    else:
        st.warning(f"{RULES_FILE} not found in {DATA_FOLDER}.")
        download_txt_file()  # Placeholder: implement this function to download the file
        return get_txt_file()  # Retry after download