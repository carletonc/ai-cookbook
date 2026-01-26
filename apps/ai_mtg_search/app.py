import os
import asyncio
import pandas as pd
import streamlit as st

from src.ui.main import validate_openai_api_key, init_sidebar


def run():
    # STREAMLIT APP CONFIGURATION
    st.set_page_config(page_title="AI MTG Card Search & Rec", layout="wide")
    st.title("🧙‍♂️ AI Magic: The Gathering Card Search")

    # Read and display README content
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    with open(readme_path, 'r') as f:
        readme_content = f.read()

    with st.expander("ℹ️&nbsp;&nbsp;About this app", expanded=True):
        st.markdown(readme_content, unsafe_allow_html=True)

    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Enter your OpenAI API Key:", type="password")

    # Only proceed if API key is provided
    if validate_openai_api_key(api_key):
        os.environ["OPENAI_API_KEY"] = api_key 
        from src.db.vectorstore import get_vector_store
        from src.llm import pipeline
        
        vectorstore = get_vector_store()

        query = st.text_input("Enter your card search query:")

        if query:
            
            response = asyncio.run(pipeline(query))
            st.markdown(response)
        

if __name__ == "__main__":
    run()