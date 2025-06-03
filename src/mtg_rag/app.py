import os
import ast
import json
import pandas as pd
import streamlit as st
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain # obsolete

#from tools import tools
from constants import METADATA_FIELDS
from utils import get_json_file, get_txt_file, get_mtg_vectorstore, clean_card_dict

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
    os.environ["OPENAI_API_KEY"] = api_key

if api_key:
    LLM = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0.0
    )    

    rules = get_txt_file()
    card_dict = get_json_file()["data"]
    
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
        batch_size=50,
        show_progress=show_progress
    )
    
    # Hide progress bar after vectorstore creation
    progress_bar.empty()
    progress_text.empty()

    # --- Sidebar filters (after DB is loaded) ---
    with st.sidebar:
        st.header("Filters & Search Settings [WIP]")
        
        # Number of results at the top
        k = st.number_input("Number of Results", min_value=1, max_value=40, value=10, step=1)
        
        st.markdown("---")  # Divider
        
        # Initialize filter values dictionary
        filter_values = {}
        
        # Core gameplay filters
        st.subheader("Card Type")
        filter_values['types'] = st.text_input(METADATA_FIELDS['types']['display_name'], "")
        filter_values['subtypes'] = st.text_input(METADATA_FIELDS['subtypes']['display_name'], "")
        filter_values['supertypes'] = st.text_input(METADATA_FIELDS['supertypes']['display_name'], "")
        
        st.markdown("---")
        
        # Mana and Color filters
        st.subheader("Mana & Colors")
        filter_values['mana_value'] = st.text_input(METADATA_FIELDS['mana_value']['display_name'], "")
        filter_values['color_identity'] = st.text_input(METADATA_FIELDS['color_identity']['display_name'], "")
        filter_values['layout'] = st.text_input(METADATA_FIELDS['layout']['display_name'], "")
        
        st.markdown("---")
        
        # Commander-specific filters
        st.subheader("Commander")
        filter_values['commander_legal'] = st.selectbox(
            METADATA_FIELDS['commander_legal']['display_name'],
            ["Any", True, False],
            index=0
        )
        filter_values['commander_eligible'] = st.selectbox(
            METADATA_FIELDS['commander_eligible']['display_name'],
            ["Any", True, False],
            index=0
        )

    # Chroma filter dict from filter_values
    chroma_filter = {}
    for key, val in filter_values.items():
        if val == "Any" or val == "":
            continue
        # For boolean values, use direct comparison
        if isinstance(val, bool):
            chroma_filter[key] = val
        # For string values in array fields, handle comma-separated values
        elif key in ['types', 'subtypes', 'supertypes', 'color_identity']:
            values = [v.strip() for v in str(val).split(',') if v.strip()]
            if values:
                chroma_filter[key] = {"$contains": values[0]}  # Using first value as filter
        # For mana value, handle numeric comparison
        elif key == 'mana_value':
            try:
                chroma_filter[key] = float(val)
            except ValueError:
                st.warning(f"Invalid mana value: {val}")
        # For layout and other strings
        else:
            chroma_filter[key] = val

    query = st.text_input("Enter your card search query:")

    if query:
        # Use similarity_search_with_score directly with filter
        results = vectorstore.similarity_search_with_score(
            query,
            k=int(k),
            #filter=chroma_filter
        )
        st.subheader("Results:")
        
        # Create a list to store the table data
        table_data = []
        for doc, score in results:
            # Extract the most relevant features
            table_data.append({
                "Name": doc.metadata.get('name', 'Unknown'),
                "Text": doc.metadata.get('text', '').replace('\n', ' '),
                "Type": doc.metadata.get('type', ''),
                "Mana Cost": doc.metadata.get('mana_cost', ''),
                "Colors": doc.metadata.get('colors', ''),
                "Power/Toughness": f"{doc.metadata.get('power', '-')}/{doc.metadata.get('toughness', '-')}" if doc.metadata.get('power') else '-',
                "Commander Legal": "✓" if doc.metadata.get('commander_legal') else "✗",
                "Keywords": doc.metadata.get('keywords', ''),
                "Score": f"{score:.6f}"
            })
        
        # Convert to DataFrame and display
        
        df = pd.DataFrame(table_data)
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn(width="medium"),
                "Text": st.column_config.TextColumn(width="large"),
                "Type": st.column_config.TextColumn(width="medium"),
                "Mana Cost": st.column_config.TextColumn(width="small"),
                "Colors": st.column_config.TextColumn(width="small"),
                "Power/Toughness": st.column_config.TextColumn(width="small"),
                "Commander Legal": st.column_config.TextColumn(width="small"),
                "Keywords": st.column_config.TextColumn(width="medium"),
                "Score": st.column_config.NumberColumn(width="small")
            }
        )
        
        # Add an expander for detailed card information
        with st.expander("Show Detailed Card Information"):
            selected_name = st.selectbox("Select a card for details:", [row["Name"] for row in table_data])
            if selected_name:
                for doc, score in results:
                    if doc.metadata.get('name') == selected_name:
                        st.markdown(doc.page_content)