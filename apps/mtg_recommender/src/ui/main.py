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
        st.session_state['k'] = st.number_input("Number of Results", min_value=1, max_value=500, value=100, step=1)
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
        
    # Chroma filter dict from filter_values / WIP
    chroma_filter = {}
    for key, val in filter_values.items():
        if val == "Any" or val == "":
            continue
        elif key in ['types', 'subtypes', 'supertypes', 'layout']:
            if val:
                chroma_filter[key] = {"$in": val}
                #else:
                #    chroma_filter[key] = {"$all": values}
        # Only process 'types' filter for testing
        elif key == 'colorIdentity':
            if val:
                chroma_filter[key] = {"$in": [COLORIDENTITY_DICT[v] for v in val]}
    if len(chroma_filter) > 1:
        chroma_filter = {"$and": [{k:v} for k,v in chroma_filter.items()]}
    

    # Chroma filter dict from filter_values
    '''
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
    '''
            
    return chroma_filter