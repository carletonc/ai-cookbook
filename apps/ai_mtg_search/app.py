import asyncio

import streamlit as st

from src.config import is_llm_configured
from src.ui.main import (
    format_timings,
    load_ui_text,
    render_card_preview,
    render_example_queries,
    render_seed_picker,
)


def _clear_picker_state():
    for key in (
        "pending_pick",
        "pending_query",
        "pending_name",
        "pending_pick_kind",
        "seed_picker_filter",
        "seed_picker_radio",
    ):
        st.session_state.pop(key, None)


def _clear_completed():
    for key in (
        "completed_query",
        "completed_status",
        "completed_text",
        "completed_timings",
        "seed_preview",
    ):
        st.session_state.pop(key, None)


def _store_completed(query: str, result) -> None:
    st.session_state["completed_query"] = query
    st.session_state["completed_status"] = result.status
    st.session_state["completed_text"] = result.text
    st.session_state["completed_timings"] = result.timings_ms
    if result.seed:
        st.session_state["seed_preview"] = result.seed
    elif result.status != "need_pick":
        st.session_state.pop("seed_preview", None)


def _render_seed_preview() -> None:
    seed = st.session_state.get("seed_preview")
    if seed:
        render_card_preview(seed, caption="Finding cards like this")


def _render_stored_result() -> None:
    _render_seed_preview()
    status = st.session_state.get("completed_status")
    text = st.session_state.get("completed_text")
    if status in ("error", "quota") and text:
        st.error(text)
    elif text:
        st.markdown(text)
    timing_line = format_timings(st.session_state.get("completed_timings"))
    if timing_line:
        st.caption(timing_line)


def _on_pick_confirmed(oracle_id: str, card_name: str) -> None:
    """Rewrite the search box and resume retrieval on the next run, picker gone."""
    choices = st.session_state.get("pending_pick") or []
    seed = next(
        (card for card in choices if card.get("scryfall_oracle_id") == oracle_id),
        None,
    )
    if seed:
        st.session_state["seed_preview"] = seed
    if card_name:
        st.session_state["search_query"] = card_name
    st.session_state["resume_oracle_id"] = oracle_id
    _clear_picker_state()


def _run_pipeline(query: str, *, seed_oracle_id: str | None = None):
    """Run the async pipeline while streaming ranker tokens into the page."""
    from src.llm import pipeline

    placeholder = st.empty()
    chunks: list[str] = []

    def on_token(piece: str) -> None:
        chunks.append(piece)
        placeholder.markdown("".join(chunks))

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

    render_example_queries()
    query = st.text_input(
        "Enter your card search query:",
        key="search_query",
        placeholder="e.g. cards like Rhystic Study",
    )

    # A changed or cleared query invalidates an in-progress disambiguation
    # and any cached write-up for a previous query.
    pending_query = st.session_state.get("pending_query")
    if pending_query is not None and pending_query != query:
        _clear_picker_state()
    if st.session_state.get("completed_query") not in (None, query):
        _clear_completed()

    # After a picker confirm we rerun with the chosen title in the search box
    # and no picker widgets, then retrieve once.
    resume_oracle_id = st.session_state.pop("resume_oracle_id", None)
    if resume_oracle_id and query:
        _render_seed_preview()
        result = _run_pipeline(query, seed_oracle_id=resume_oracle_id)
        if result.status == "need_pick":
            st.session_state["pending_pick"] = result.choices or []
            st.session_state["pending_query"] = query
            st.session_state["pending_name"] = result.name
            st.session_state["pending_pick_kind"] = result.pick_kind
            st.rerun()
        _store_completed(query, result)
        return

    if query and st.session_state.get("completed_query") == query:
        _render_stored_result()
        return

    if st.session_state.get("pending_pick") and st.session_state.get("pending_query") == query:
        render_seed_picker(
            st.session_state["pending_pick"],
            st.session_state.get("pending_name"),
            pick_kind=st.session_state.get("pending_pick_kind"),
            on_confirm=_on_pick_confirmed,
        )
        return

    if query:
        result = _run_pipeline(query)

        if result.status == "need_pick":
            st.session_state["pending_pick"] = result.choices or []
            st.session_state["pending_query"] = query
            st.session_state["pending_name"] = result.name
            st.session_state["pending_pick_kind"] = result.pick_kind
            st.rerun()
        _store_completed(query, result)
        if result.seed:
            st.rerun()


if __name__ == "__main__":
    run()
