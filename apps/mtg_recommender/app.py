# ---  SQLite patch for Streamlit Cloud ---
try:
    import sqlite3
    if sqlite3.sqlite_version_info < (3, 35, 0):
        import sys
        import pysqlite3
        sys.modules["sqlite3"] = pysqlite3
except Exception:
    # If anything fails, fall back silently. Better to run than crash.
    pass

import os
import pandas as pd
import streamlit as st

from src.constants import METADATA_FIELDS
from src.data.utils import load_json_file, load_txt_file, get_vector_store
from src.ui.main import validate_openai_api_key, init_sidebar
from src.llm import query_llm, get_context

# STREAMLIT APP CONFIGURATION
st.set_page_config(page_title="MTG Card Search w/RAG", layout="wide")
st.title("🧙‍♂️ Magic: The Gathering Card Search")

# Read and display README content
readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
with open(readme_path, 'r') as f:
    readme_content = f.read()

with st.expander("ℹ️ About this app", expanded=False):
    st.markdown(readme_content)

with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")

# Only proceed if API key is provided
if validate_openai_api_key(api_key):
    os.environ["OPENAI_API_KEY"] = api_key  

    rules = load_txt_file()
    # card_df = load_json_file()
    
    vectorstore = get_vector_store()
    # currently irrelevant
    chroma_filter = init_sidebar()

    query = st.text_input("Enter your card search query:")

    if query:
        context = get_context(query, K=st.session_state.get('k', 100)) #
        response = query_llm(query, context)
        st.markdown(response)