import asyncio
import time

import streamlit as st

from src.config import is_llm_configured
from src.ui.main import (
    format_timings,
    load_ui_text,
    render_card_preview,
    render_example_queries,
    render_seed_picker,
)

_SEARCH_KEY = "search"
_TOKEN_FLUSH_S = 0.1


def _clear_search() -> None:
    st.session_state.pop(_SEARCH_KEY, None)
    for key in ("seed_picker_filter", "seed_picker_radio"):
        st.session_state.pop(key, None)


def _store(query: str, result) -> None:
    st.session_state[_SEARCH_KEY] = {"query": query, "result": result}


def _render_result(result) -> None:
    if result.seed:
        render_card_preview(result.seed, caption="Finding cards like this")
    if result.status in ("error", "quota") and result.text:
        st.error(result.text)
    elif result.text:
        st.markdown(result.text)
    timing_line = format_timings(result.timings_ms)
    if timing_line:
        st.caption(timing_line)


def _on_pick_confirmed(oracle_id: str, card_name: str) -> None:
    """Runs before widgets on the next script run. Do not write search_query here."""
    state = st.session_state.get(_SEARCH_KEY) or {}
    result = state.get("result")
    choices = (result.choices if result is not None else None) or []
    seed = next(
        (card for card in choices if card.get("scryfall_oracle_id") == oracle_id),
        None,
    )
    if seed:
        st.session_state["resume_seed"] = seed
    if card_name:
        st.session_state["pending_query"] = card_name
    st.session_state["resume_oracle_id"] = oracle_id
    _clear_search()


def _apply_pending_query() -> None:
    """Copy into the search box key before that widget is instantiated."""
    pending = st.session_state.pop("pending_query", None)
    if pending is not None:
        st.session_state["search_query"] = pending


@st.cache_resource(show_spinner=False)
def _encoder():
    from src.embeddings import _get_encoder

    return _get_encoder()


def _run_pipeline(query: str, *, seed_oracle_id: str | None = None):
    """Run the async pipeline, flushing ranker tokens about 10 times per second."""
    from src.llm import pipeline

    _encoder()

    placeholder = st.empty()
    chunks: list[str] = []
    last_flush = 0.0

    def on_token(piece: str) -> None:
        nonlocal last_flush
        chunks.append(piece)
        now = time.monotonic()
        if now - last_flush >= _TOKEN_FLUSH_S:
            placeholder.markdown("".join(chunks))
            last_flush = now

    with st.spinner("Searching the card pool..."):
        result = asyncio.run(
            pipeline(query, seed_oracle_id=seed_oracle_id, on_token=on_token)
        )

    # Write after the spinner so Streamlit does not drop tokens streamed
    # into this placeholder from inside the spinner context.
    if result.status in ("error", "quota") and result.text:
        placeholder.error(result.text)
    elif result.text:
        placeholder.markdown(result.text)

    timing_line = format_timings(result.timings_ms)
    if timing_line:
        st.caption(timing_line)
    return result


def run():
    st.set_page_config(page_title="AI MTG Card Search & Rec", layout="wide")
    st.title("🧙‍♂️ AI Magic: The Gathering Card Search")

    with st.expander("ℹ️&nbsp;&nbsp;About this app", expanded=False):
        st.markdown(load_ui_text("ABOUT.md"), unsafe_allow_html=True)

    with st.expander("⚙️&nbsp;&nbsp;Technical decisions", expanded=False):
        st.markdown(load_ui_text("TECHNICAL.md"), unsafe_allow_html=True)

    if not is_llm_configured():
        st.error(
            "This demo is not configured yet — missing an LLM API key. "
            "Add `GROQ_API_KEY` (or `LLM_API_KEY`) to the app secrets / `.env`."
        )
        return

    _apply_pending_query()
    render_example_queries()
    query = st.text_input(
        "Enter your card search query:",
        key="search_query",
        placeholder="e.g. cards like Rhystic Study",
    )

    state = st.session_state.get(_SEARCH_KEY)
    if state is not None and state.get("query") != query:
        _clear_search()
        state = None

    resume_oracle_id = st.session_state.pop("resume_oracle_id", None)
    resume_seed = st.session_state.pop("resume_seed", None)
    if resume_oracle_id and query:
        if resume_seed:
            render_card_preview(resume_seed, caption="Finding cards like this")
        result = _run_pipeline(query, seed_oracle_id=resume_oracle_id)
        _store(query, result)
        if result.status == "need_pick":
            st.rerun()
        return

    if state is not None and state.get("query") == query:
        result = state["result"]
        if result.status == "need_pick":
            render_seed_picker(
                result.choices or [],
                result.name,
                pick_kind=result.pick_kind,
                on_confirm=_on_pick_confirmed,
            )
        else:
            _render_result(result)
        return

    if query:
        result = _run_pipeline(query)
        _store(query, result)
        if result.status == "need_pick" or result.seed:
            st.rerun()


if __name__ == "__main__":
    run()
