import os
import json
import requests
import ast
import streamlit as st
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = "data"
CARDS_FILE = "AtomicCards.json"
RULES_FILE = "MagicCompRules_21031101.txt"
JSON_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, CARDS_FILE)
TXT_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, RULES_FILE)
PERSIST_PATH = os.path.join(SCRIPT_DIR, DATA_FOLDER, "chroma_db")

def fetch_mtgjson_data():
    """Fetch data from MTGJSON and save to file."""
    url = "https://mtgjson.com/api/v5/AtomicCards.json"
    print(f"Fetching data from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f)


def fetch_mtg_rules():
    """Fetch Magic Comp Rules and save to file."""
    url = "https://media.wizards.com/2025/downloads/MagicCompRules%2020250404.txt"
    print(f"Fetching rules from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    text = response.text
    os.makedirs(os.path.dirname(TXT_PATH), exist_ok=True)
    with open(TXT_PATH, "w") as f:
        f.write(text)


def get_json_file():
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r") as f:
            data = json.load(f)
        return data
    else:
        with st.spinner(f"{CARDS_FILE} not found in {DATA_FOLDER}. Downloading..."):
            fetch_mtgjson_data()
        return get_json_file()


def get_txt_file():
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
    Remove unnecessary keys from card data and convert values to string for vectorstore ingestion.
    """
    cleaned = {}
    for k, v in card_dict.items():
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    item.pop("foreignData", None)
                    item.pop("printings", None)
                    item.pop("purchaseUrls", None)
        cleaned[k] = str(v)
    return cleaned


def get_mtg_vectorstore(card_dict, persist_path=PERSIST_PATH, collection_name="mtg-poc", embedding_model="text-embedding-3-small", batch_size=500, show_progress=None):
    """
    Create or load a Chroma vectorstore for MTG cards.
    - card_dict: dict of card_name -> card_data (as string or list of dicts)
    - persist_path: path to store the vector DB
    - collection_name: Chroma collection name
    - embedding_model: OpenAI embedding model name
    - batch_size: number of docs per batch
    - show_progress: optional callback for progress (e.g., Streamlit progress bar)
    """
    # Ensure the persist directory exists (parent only, not the full path)
    #os.makedirs(os.path.dirname(persist_path), exist_ok=True)
    #if not os.path.exists(persist_path):
    #    os.makedirs(persist_path, exist_ok=True)
    embedding = OpenAIEmbeddings(model=embedding_model)
    docs = []
    for card_name, raw_str in card_dict.items():
        try:
            card_data = ast.literal_eval(raw_str)
            text_blob = ",\n".join(
                f"{k}: {v}" for entry in card_data for k, v in entry.items()
            )
            docs.append(
                Document(
                    page_content=text_blob,
                    metadata={"name": card_name}
                )
            )
        except Exception as e:
            print(f"⚠️ Skipping {card_name} due to error: {e}")
            
    def batch(iterable, size=batch_size):
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]
            
    if os.path.exists(persist_path) and os.path.isdir(persist_path):
        vectorstore = Chroma(
            persist_directory=persist_path,
            collection_name=collection_name,
            embedding_function=embedding
        )
    else:
        vectorstore = Chroma(
            persist_directory=persist_path,
            collection_name=collection_name,
            embedding_function=embedding
        )
        
        total = len(docs)
        for i, chunk in enumerate(batch(docs, size=batch_size)):
            vectorstore.add_documents(chunk)
            
            if show_progress:
                show_progress(min((i+1)*batch_size/total, 1.0))
                
        vectorstore.persist()
    return vectorstore