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
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain # obsolete

from constants import METADATA_FIELDS
from utils import load_json_file, load_txt_file, get_vector_store, show_results_table, show_dropdown_details
from sidebar import validate_openai_api_key, init_sidebar

# STREAMLIT APP CONFIGURATION
st.set_page_config(page_title="MTG Card Search", layout="wide")
st.title("🤖 MTG Card Search")

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
    
    LLM = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0.0
    )    

    rules = load_txt_file()
    # card_df = load_json_file()
    
    vectorstore = get_vector_store()
    k, chroma_filter = init_sidebar()

    query = st.text_input("Enter your card search query:")

    if query:
        # Use similarity_search_with_score directly with filter
        results = vectorstore.similarity_search_with_score(
            query,
            k=int(k),
            filter=chroma_filter if chroma_filter else None
        )
        
        show_results_table(results)
        show_dropdown_details(results)