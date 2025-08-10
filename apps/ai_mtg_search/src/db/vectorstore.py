import os
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import numpy as np
import streamlit as st
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

from src.constants import METADATA_FIELDS
from src.db.utils import load_json_file, load_txt_file 

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "mtg-cards"
PINECONE_ENVIRONMENT = "us-east-1-aws"  # Update with your preferred environment
EMBEDDING_MODEL = "text-embedding-3-small"
DIMENSION = 1536  # Dimension for text-embedding-3-small



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
        
        name = row['faceName']
        text = row['text'] if pd.notna(row['text']) else ''
        page_content = f'{name}:{text}'
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
                index_name=index_name,
                text_key="content"
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
            model=EMBEDDING_MODEL,
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
                embedding=embeddings,
                text_key="content"
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
    
if __name__ == "__main__":
    #reset_vector_store(index_name=PINECONE_INDEX_NAME)
    get_vector_store()