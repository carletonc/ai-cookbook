"""
Configuration for the retrieval app.

Card data is owned by the external `mtg-db` repo; this app only reads.
Values here must stay aligned with what that pipeline wrote.

Every lookup is lazy. Resolving at import time would crash the headless
Streamlit smoke test in CI, where no .env exists.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Must match mtg-db's embed job. Cosine distance makes vector magnitude
# irrelevant, so a normalizing backend (fastembed) is comparable to a
# non-normalizing one (sentence-transformers) — but the weights and
# dimension must be identical.
EMBED_MODEL = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "fastembed")

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-nano")


def _from_streamlit_secrets(key: str) -> str | None:
    """Read a Streamlit secret, tolerating execution outside a Streamlit runtime."""
    try:
        import streamlit as st

        return st.secrets.get(key)
    except Exception:
        return None


def get_database_url() -> str:
    """Resolve the Neon connection string, preferring the environment."""
    url = os.getenv("DATABASE_URL") or _from_streamlit_secrets("DATABASE_URL")
    if not url:
        raise EnvironmentError(
            "Missing DATABASE_URL. Copy .env.example to .env and set the Neon "
            "connection string, or add it to Streamlit secrets."
        )
    return url


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or _from_streamlit_secrets("OPENAI_API_KEY")
