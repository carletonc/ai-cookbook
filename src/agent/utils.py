import streamlit as st

from constants import SYSTEM_PROMPT

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
    
# Sidebar for configuration
def init_sidebar():
    """Render sidebar UI for model selection and agent configuration. Returns selected model, temperature, and memory limit."""
    with st.sidebar:
        # Add model selection
        model_options = ["gpt-4.1-mini", "gpt-3.5-turbo"]
        selected_model = st.selectbox("Select Model:", model_options, index=0)
        temperature = st.slider("Temperature:", min_value=0.0, max_value=1.0, value=0.5, step=0.1)
        memory_history_limit = st.number_input("Memory Limit:", min_value=1, max_value=100, value=50, step=1)
        
        st.markdown("### Current System Prompt:")
        st.info(SYSTEM_PROMPT)
        return {
            'model': selected_model, 
            'temperature': temperature, 
            'memory_limit': memory_history_limit
        }