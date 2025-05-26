import os
import ast
import json
import streamlit as st
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI, ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain # obsolete

from langchain_community.vectorstores import Chroma
from langchain.schema import Document

#from tools import tools
from utils import get_json_file, get_txt_file

from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LLM = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.0
)


rules = get_txt_file()
card_dict = get_json_file()["data"]
# Remove 'flavorText' from inner dicts
for k, v in card_dict.items():
    if isinstance(v, list):
        for item in v:
            if isinstance(item, dict):
                item.pop("foreignData", None)
                item.pop("printings", None)
                item.pop("purchaseUrls", None)
card_dict = {k: str(v) for k, v in card_dict.items()}

def get_retriever():
    # Set your persist path
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    persist_path = os.path.join(SCRIPT_DIR, "data", "chroma_db")
    collection_name = "mtg-poc"
    # Initialize embedding model
    embedding = OpenAIEmbeddings(model="text-embedding-3-small")
    # Create documents
    docs = []
    for card_name, raw_str in card_dict.items():
        try:
            card_data = ast.literal_eval(raw_str)
            text_blob = "\n".join(
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
    # Define batching helper
    def batch(iterable, size=500):
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]
    # ✅ Check if DB already exists
    if os.path.exists(persist_path) and os.path.isdir(persist_path):
        with st.spinner("🔁 Loading existing Chroma vectorstore..."):
            vectorstore = Chroma(
                persist_directory=persist_path,
                collection_name=collection_name,
                embedding_function=embedding
            )
    else:
        with st.spinner("🚧 Creating new Chroma vectorstore..."):
            vectorstore = Chroma(
                persist_directory=persist_path,
                collection_name=collection_name,
                embedding_function=embedding
            )
            # Batch ingest documents with Streamlit progress bar
            progress_bar = st.progress(0)
            total = len(docs)
            for i, chunk in enumerate(batch(docs, size=500)):
                vectorstore.add_documents(chunk)
                progress_bar.progress(min((i+1)*500/total, 1.0))
            vectorstore.persist()
            st.success("✅ Chroma vectorstore saved to disk.")
    retriever = vectorstore.as_retriever(search_kwargs={"k": 25})
    return retriever


# STREAMLIT APP

# Page configuration
st.set_page_config(page_title="MTG Card Search", layout="wide")
# Main content area
st.title("🤖 MTG Card Search")
#st.header("MTG Card Search")
st.markdown("This app allows you to search for Magic: The Gathering cards using a simple LLM agent.\nRight now it merely stores cards in a vectorDB and retrieves the closest cards, but there are issues with accuracy (precision & recall) that must be resolved for it to work optimally. Future iterations will resolve this.")


# Sidebar for API key
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    #os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY  # Keep hardcoded logic
    #st.markdown("### Current System Prompt:")
    #st.info("SYSTEM_PROMPT")

# Only proceed if API key is provided
if api_key:
    retriever = get_retriever()

    # Text input for card query
    query = st.text_input("Enter your card search query:")
    
    if query:
        results = retriever.invoke(query)
        st.subheader("Results:")
        for doc in results:
            st.markdown(f"**{doc.metadata['name']}**\n\n{doc.page_content}")