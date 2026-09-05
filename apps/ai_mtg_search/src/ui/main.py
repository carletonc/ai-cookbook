from collections.abc import Callable
from pathlib import Path

import streamlit as st

from src.ui.card_links import (
    fetch_image_bytes,
    picker_haystack,
    picker_option_label,
    scryfall_card_url,
    scryfall_image_url,
    tcgplayer_search_url,
)

_UI_DIR = Path(__file__).resolve().parent

# Clickable demos for visitors who do not know Magic well.
EXAMPLE_QUERIES = [
    "cards like Rhystic Study",
    "draw a card when a creature enters",
    "make squirrel tokens",
    "counter target spell",
]


@st.cache_data(show_spinner=False)
def load_ui_text(name: str) -> str:
    """Read a markdown file sitting next to this module. Cached across reruns."""
    return (_UI_DIR / name).read_text(encoding="utf-8")


def _combat_stats(card: dict) -> str | None:
    if card.get("power") is not None or card.get("toughness") is not None:
        return f"{card.get('power') or '?'}/{card.get('toughness') or '?'}"
    if card.get("loyalty") is not None:
        return f"loyalty {card['loyalty']}"
    return None


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def _cached_scryfall_image(url: str) -> bytes | None:
    return fetch_image_bytes(url)


def render_card_preview(card: dict, *, caption: str | None = None) -> None:
    """Art, type, printed cost, and shop links for a resolved seed card."""
    if caption:
        st.caption(caption)
    image_url = scryfall_image_url(card)
    scryfall = scryfall_card_url(card)
    tcgplayer = tcgplayer_search_url(card)
    art, details = st.columns([1, 2])

    with art:
        image = _cached_scryfall_image(image_url) if image_url else None
        if image:
            st.image(image, width=220)
        else:
            st.caption("No preview image — use the Scryfall link.")

    with details:
        st.markdown(f"**{card.get('name') or '(unnamed)'}**")
        if card.get("type_line"):
            st.caption(card["type_line"])
        links = []
        if scryfall:
            links.append(f"[Scryfall]({scryfall})")
        if tcgplayer:
            links.append(f"[TCGPlayer]({tcgplayer})")
        if links:
            st.markdown(" · ".join(links))

        fields = [
            ("mana", card.get("mana_cost")),
            ("Color Identity", "/".join(card.get("color_identity") or []) or None),
            ("stats", _combat_stats(card)),
            ("commander", "legal" if card.get("commander_legal") else "not legal"),
            ("edhrec", card.get("edhrec_rank")),
        ]
        shown = [f"**{label}:** {value}" for label, value in fields if value not in (None, "")]
        if shown:
            st.markdown("  \n".join(shown))
        if card.get("oracle_text"):
            st.markdown(card["oracle_text"].replace("\n", "  \n"))


def render_example_queries() -> None:
    """Hint + buttons that fill the main search box via session state."""
    st.caption(
        "Name a card for alternatives, or describe an effect in plain English."
    )
    st.markdown("**Try these:**")
    for row in (EXAMPLE_QUERIES[:2], EXAMPLE_QUERIES[2:]):
        cols = st.columns(2)
        for col, example in zip(cols, row):
            with col:
                if st.button(example, key=f"example_{example}"):
                    st.session_state["search_query"] = example
                    st.rerun()


def format_timings(timings: dict[str, int] | None) -> str | None:
    if not timings:
        return None
    order = ("planner", "resolve", "retrieve", "rank")
    parts = [f"{key} {timings[key]}ms" for key in order if key in timings]
    if not parts:
        parts = [f"{k} {v}ms" for k, v in timings.items()]
    return " · ".join(parts) if parts else None


def render_seed_picker(
    choices: list[dict],
    name: str | None,
    *,
    pick_kind: str | None = "contains",
    on_confirm: Callable[[str, str], None] | None = None,
) -> None:
    """
    Name-only radio plus a structured preview of the selected card.

    Streamlit radios are plain text (no markdown or links), so the option
    list stays scannable and the image / shop links live on the selection.
    `on_confirm` is a button callback so it runs before widgets on the
    next script run. Filtering reruns the page but not the pipeline.
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
            if filter_text in picker_haystack(card)
        ]

    if not visible:
        st.warning("No cards in this list match that filter. Clear the filter to see all matches.")
        return

    by_id = {card["scryfall_oracle_id"]: card for card in visible}
    selected_id = st.radio(
        "Which card?",
        options=list(by_id),
        format_func=lambda oracle_id: picker_option_label(
            by_id.get(oracle_id) or {"name": oracle_id}
        ),
        key="seed_picker_radio",
        label_visibility="collapsed",
    )
    selected = by_id.get(selected_id) or visible[0]
    render_card_preview(selected)

    st.button(
        "Find Similar Cards",
        type="primary",
        key="seed_picker_confirm",
        on_click=on_confirm,
        args=(selected["scryfall_oracle_id"], selected.get("name") or ""),
        disabled=on_confirm is None,
    )
