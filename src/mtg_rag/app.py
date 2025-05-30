import os
import ast
import json
import streamlit as st
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain # obsolete

#from tools import tools
from utils import get_json_file, get_txt_file, get_mtg_vectorstore, clean_card_dict

rules = get_txt_file()
card_dict = get_json_file()["data"]
card_dict = clean_card_dict(card_dict)

# STREAMLIT APP
st.set_page_config(page_title="MTG Card Search", layout="wide")
st.title("🤖 MTG Card Search")
st.write("This app allows you to search for Magic: The Gathering cards using a simple LLM agent.\nRight now it merely stores cards in a vectorDB and retrieves the closest cards, but there are issues with accuracy (precision & recall) that must be resolved for it to work optimally. Future iterations will resolve this.")

with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    os.environ["OPENAI_API_KEY"] = api_key

if api_key:
    LLM = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0.0
    )
    
    # Use Streamlit progress bar for feedback
    progress_text = st.empty()
    progress_text.text("Building Chroma vectorstore...")
    progress_bar = st.progress(0)
    
    def show_progress(val):
        progress_bar.progress(val)
        
    vectorstore = get_mtg_vectorstore(
        card_dict,
        #persist_path=persist_path,
        collection_name="mtg-poc",
        embedding_model="text-embedding-3-small",
        batch_size=500,
        show_progress=show_progress
    )
    
    # Hide progress bar after vectorstore creation
    progress_bar.empty()
    progress_text.empty()
    vectorstore = vectorstore.as_retriever(search_kwargs={"k": 5})
    query = st.text_input("Enter your card search query:")
    
    if query:
        results = vectorstore.invoke(query)
        st.subheader("Results:")
        for doc in results:
            st.markdown(f"**{doc.metadata['name']}**\n\n{doc.page_content}")