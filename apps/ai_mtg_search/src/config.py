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

# OpenAI-compatible chat host. Defaults to Groq free-tier demo settings.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
LLM_DAILY_REQUEST_CAP = int(os.getenv("LLM_DAILY_REQUEST_CAP", "800"))


def _from_streamlit_secrets(key: str) -> str | None:
    """Read a Streamlit secret, tolerating execution outside a Streamlit runtime."""
    try:
        import streamlit as st

        return st.secrets.get(key)
    except Exception:
        return None


def get_database_url() -> str:
    """
    Resolve the Neon connection string.

    Prefer `DATABASE_URL_READONLY` (least-privilege reader role) over
    `DATABASE_URL` so a compromised app cannot write even if application
    code is wrong. Streamlit secrets follow the same order.
    """
    for key in ("DATABASE_URL_READONLY", "DATABASE_URL"):
        url = os.getenv(key) or _from_streamlit_secrets(key)
        if url:
            return url
    raise EnvironmentError(
        "Missing DATABASE_URL_READONLY (preferred) or DATABASE_URL. "
        "Copy .env.example to .env and set a read-only Neon connection "
        "string, or add it to Streamlit secrets."
    )


def get_llm_api_key() -> str | None:
    """
    Resolve the chat LLM API key (Groq / HF / OpenAI / xAI).

    Prefer LLM_API_KEY, then common provider-specific names.
    """
    for key in (
        "LLM_API_KEY",
        "GROQ_API_KEY",
        "HF_TOKEN",
        "OPENAI_API_KEY",
        "GROK_API_KEY",
        "XAI_API_KEY",
    ):
        value = os.getenv(key) or _from_streamlit_secrets(key)
        if value:
            return value
    return None


def is_llm_configured() -> bool:
    return bool(get_llm_api_key())


def get_openai_api_key() -> str | None:
    """Backward-compatible alias used by eval scripts."""
    return get_llm_api_key()
