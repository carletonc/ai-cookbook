import streamlit as st


def validate_openai_api_key(api_key):
    """Return True if the key works. Warns in the sidebar when it doesn't."""
    if not api_key:
        # No key entered yet; do not warn
        return False
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        client.models.list()
        return True
    except Exception:
        with st.sidebar:
            st.warning("Invalid OpenAI API key. Please check your key and try again.")
        return False
