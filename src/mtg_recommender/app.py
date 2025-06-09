import os
import pandas as pd
import streamlit as st
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain # obsolete

#from tools import tools
from constants import METADATA_FIELDS
from utils import load_json_file, load_txt_file, get_vector_store

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

    rules = load_txt_file()
    # card_df = load_json_file()
    
    vectorstore = get_vector_store()
    

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
        filter_values['manaValue'] = st.text_input(METADATA_FIELDS['manaValue']['display_name'], "")
        filter_values['colorIdentity'] = st.text_input(METADATA_FIELDS['colorIdentity']['display_name'], "")
        filter_values['layout'] = st.text_input(METADATA_FIELDS['layout']['display_name'], "")
        
        st.markdown("---")
        
        # Commander-specific filters
        st.subheader("Commander")
        filter_values['legalities.commander'] = st.selectbox(
            METADATA_FIELDS['legalities.commander']['display_name'],
            ["Any", "Legal", "Not Legal"],
            index=0
        )
        filter_values['leadershipSkills.commander'] = st.selectbox(
            METADATA_FIELDS['leadershipSkills.commander']['display_name'],
            ["Any", True, False],
            index=0
        )

    # Chroma filter dict from filter_values
    chroma_filter = {}
    for key, val in filter_values.items():
        if val == "Any" or val == "":
            continue
        # For legality fields
        if key == 'legalities.commander':
            if val != "Any":
                chroma_filter[key] = (val == "Legal")
        # For leadership/eligibility fields
        elif key == 'leadershipSkills.commander':
            if val != "Any":
                chroma_filter[key] = bool(val)
        # For string values in array fields, handle comma-separated values
        elif key in ['types', 'subtypes', 'supertypes', 'colorIdentity']:
            values = [v.strip() for v in str(val).split(',') if v.strip()]
            if values:
                if len(values) == 1:
                    # Single value: just check if array contains it
                    chroma_filter[key] = {"$contains": values[0]}
                else:
                    # Multiple values: check if array contains ALL values
                    chroma_filter[key] = {"$all": values}
        # For mana value, handle numeric comparison
        elif key == 'manaValue':
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
            filter=chroma_filter if chroma_filter else None
        )
        st.subheader("Results:")
        
        # Create a list to store the table data
        table_data = []
        for doc, score in results:
            # Extract the most relevant features
            table_data.append({
                "Name": doc.metadata.get('name', doc.metadata.get('cardName', 'Unknown')),
                "Text": doc.metadata.get('text', '').replace('\n', ' '),
                "Type": doc.metadata.get('type', ''),
                "Mana Cost": doc.metadata.get('manaCost', ''),
                "Colors": doc.metadata.get('colors', ''),
                "Power/Toughness": f"{doc.metadata.get('power', '-')}/{doc.metadata.get('toughness', '-')}" if doc.metadata.get('power') else '-',
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
                "Keywords": st.column_config.TextColumn(width="medium"),
                "Score": st.column_config.NumberColumn(width="small")
            }
        )
        
        # Add an expander for detailed card information
        with st.expander("Show Detailed Card Information"):
            selected_name = st.selectbox("Select a card for details:", [row["Name"] for row in table_data])
            if selected_name:
                selected_card = None
                for doc, score in results:
                    if doc.metadata.get('name', doc.metadata.get('cardName')) == selected_name:
                        selected_card = doc
                        break
                
                if selected_card:
                    # Display comprehensive card information
                    st.write("### Card Details")
                    details = {
                        "Name": selected_card.metadata.get('name', selected_card.metadata.get('cardName')),
                        "Type": selected_card.metadata.get('type'),
                        "Mana Cost": selected_card.metadata.get('manaCost'),
                        "Colors": selected_card.metadata.get('colors', ''),
                        "Color Identity": selected_card.metadata.get('colorIdentity', ''),
                        "Power/Toughness": f"{selected_card.metadata.get('power', '-')}/{selected_card.metadata.get('toughness', '-')}" if selected_card.metadata.get('power') else None,
                        "Keywords": selected_card.metadata.get('keywords', ''),
                        "Oracle Text": selected_card.metadata.get('text'),
                    }
                    
                    for key, value in details.items():
                        if value:
                            st.write(f"**{key}:** {value}")
                    
                    # Display legalities
                    st.write("### Legalities")
                    legalities = {k.replace('legalities.', ''): v 
                                for k, v in selected_card.metadata.items() 
                                if k.startswith('legalities.')}
                    
                    cols = st.columns(3)
                    for idx, (format_name, legal) in enumerate(legalities.items()):
                        with cols[idx % 3]:
                            st.write(f"**{format_name.title()}:** {'Legal' if legal else 'Not Legal'}")