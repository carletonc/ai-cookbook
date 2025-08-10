import streamlit as st
from ..constants import METADATA_FIELDS
from .config import TYPES, SUBTYPES, SUPERTYPES, COLORIDENTITY_DICT, LAYOUT



def validate_openai_api_key(api_key):
    """Check if the OpenAI API key is valid. Returns True if valid, False otherwise. Shows a warning in the sidebar if invalid."""
    if not api_key:
        # No key entered yet; do not warn
        return False
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        # Make a minimal call (list models)
        client.models.list()
        return True
    except Exception:
        with st.sidebar:
            st.warning("Invalid OpenAI API key. Please check your key and try again.")
        return False


def init_sidebar():
    """Render sidebar UI for filters and search settings. Returns number of results and Chroma filter dict."""
    # --- Sidebar filters (after DB is loaded) ---
    with st.sidebar:
        st.header("Filters & Search Settings [WIP - not functioning]")
        
        # Number of results at the top
        st.session_state['k'] = st.number_input(
            "Number of Results", 
            min_value=1, 
            max_value=500, 
            value=30, 
            step=1
        )
        st.markdown("---")  # Divider
        
        # Initialize filter values dictionary
        filter_values = {}
        
        # Core gameplay filters
        st.subheader("Card Type")
        filter_values['types'] = st.multiselect(METADATA_FIELDS['types']['display_name'], TYPES, accept_new_options=False)
        filter_values['subtypes'] = st.multiselect(METADATA_FIELDS['subtypes']['display_name'], SUBTYPES, accept_new_options=False)
        filter_values['supertypes'] = st.multiselect(METADATA_FIELDS['supertypes']['display_name'], SUPERTYPES, accept_new_options=False)
        st.markdown("---")
        
        # Mana and Color filters
        st.subheader("Mana & Colors")
        filter_values['manaValue'] = st.text_input(METADATA_FIELDS['manaValue']['display_name'], "")
        filter_values['colorIdentity'] = st.multiselect(METADATA_FIELDS['colorIdentity']['display_name'], list(COLORIDENTITY_DICT.keys()), accept_new_options=False)
        filter_values['layout'] = st.multiselect(METADATA_FIELDS['layout']['display_name'], LAYOUT, accept_new_options=False)
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
        
    # Filter dict from filter_values / WIP
    filter = {}
    for key, val in filter_values.items():
        if val == "Any" or val == "":
            continue
        elif key in ['types', 'subtypes', 'supertypes', 'layout']:
            if val:
                filter[key] = {"$in": val}
                #else:
                #    filter[key] = {"$all": values}
        # Only process 'types' filter for testing
        elif key == 'colorIdentity':
            if val:
                filter[key] = {"$in": [COLORIDENTITY_DICT[v] for v in val]}
    if len(filter) > 1:
        filter = {"$and": [{k:v} for k,v in filter.items()]}
    
    return filter