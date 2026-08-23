from pathlib import Path

import streamlit as st

_UI_DIR = Path(__file__).resolve().parent


def load_ui_text(name: str) -> str:
    """Read a markdown (or other text) file sitting next to this module."""
    return (_UI_DIR / name).read_text(encoding="utf-8")


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
