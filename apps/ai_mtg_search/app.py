import asyncio

import streamlit as st

from src.config import is_llm_configured
from src.ui.main import (
    format_timings,
    load_ui_text,
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

    if result.status in ("error", "quota") and result.text:
        placeholder.error(result.text)
    elif result.text and not chunks:
        placeholder.markdown(result.text)
    elif result.text and chunks and "".join(chunks) != result.text:
        # Prefer the final assembled answer if stream and result diverge.
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

    # A changed or cleared query invalidates an in-progress disambiguation.
    pending_query = st.session_state.get("pending_query")
    if pending_query is not None and pending_query != query:
        _clear_picker_state()

    if st.session_state.get("pending_pick") and st.session_state.get("pending_query") == query:
        choices = st.session_state["pending_pick"]
        oracle_id = render_seed_picker(
            choices,
            st.session_state.get("pending_name"),
            pick_kind=st.session_state.get("pending_pick_kind"),
        )
        if oracle_id:
            result = _run_pipeline(query, seed_oracle_id=oracle_id)
            _clear_picker_state()
            if result.status == "need_pick":
                st.session_state["pending_pick"] = result.choices or []
                st.session_state["pending_query"] = query
                st.session_state["pending_name"] = result.name
                st.session_state["pending_pick_kind"] = result.pick_kind
                st.rerun()
        return

    if query:
        result = _run_pipeline(query)

        if result.status == "need_pick":
            st.session_state["pending_pick"] = result.choices or []
            st.session_state["pending_query"] = query
            st.session_state["pending_name"] = result.name
            st.session_state["pending_pick_kind"] = result.pick_kind
            st.rerun()


if __name__ == "__main__":
    run()
