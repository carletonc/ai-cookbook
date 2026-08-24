from pathlib import Path

import streamlit as st

_UI_DIR = Path(__file__).resolve().parent
_SNIPPET_LEN = 140


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


def picker_label(card: dict) -> str:
    """Uniform radio label: full name, type line, and a short oracle snippet."""
    name = card.get("name") or "(unnamed)"
    type_line = card.get("type_line") or ""
    text = (card.get("oracle_text") or "").replace("\n", " ").strip()
    if len(text) > _SNIPPET_LEN:
        text = text[: _SNIPPET_LEN - 1].rstrip() + "…"
    lines = [name]
    if type_line:
        lines.append(type_line)
    if text:
        lines.append(text)
    return "\n".join(lines)


def render_seed_picker(
    choices: list[dict],
    name: str | None,
    *,
    pick_kind: str | None = "contains",
) -> str | None:
    """
    Show every matching seed card with the same row layout.

    Returns the chosen `scryfall_oracle_id` when the user confirms, else None.
    A filter box narrows the in-memory list for long character lines (Jace);
    it does not change which cards are available.
    """
    if pick_kind == "fuzzy":
        st.info(
            f"We couldn't match **{name or 'that name'}** exactly. "
            "Are any of these what you meant?"
        )
    else:
        st.info(
            f"Several cards match **{name or 'that name'}**. "
            "Pick the one you meant, then continue."
        )

    filter_text = st.text_input(
        "Filter this list",
        key="seed_picker_filter",
        placeholder="Type to narrow by name, type, or text…",
    ).strip().lower()

    visible = choices
    if filter_text:
        visible = [
            card
            for card in choices
            if filter_text in picker_label(card).lower()
        ]

    if not visible:
        st.warning("No cards in this list match that filter. Clear the filter to see all matches.")
        return None

    labels = [picker_label(card) for card in visible]
    selected_label = st.radio(
        "Which card?",
        options=labels,
        key="seed_picker_radio",
        label_visibility="collapsed",
    )
    selected = visible[labels.index(selected_label)]

    if st.button("Find alternatives", type="primary", key="seed_picker_confirm"):
        return selected["scryfall_oracle_id"]
    return None
