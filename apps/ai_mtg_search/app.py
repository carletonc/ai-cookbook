import asyncio
import os

import streamlit as st

from src.ui.main import load_ui_text, render_seed_picker, validate_openai_api_key


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


def run():
    st.set_page_config(page_title="AI MTG Card Search & Rec", layout="wide")
    st.title("🧙‍♂️ AI Magic: The Gathering Card Search")

    with st.expander("ℹ️&nbsp;&nbsp;About this app", expanded=True):
        st.markdown(load_ui_text("ABOUT.md"), unsafe_allow_html=True)

    with st.sidebar:
        st.header("Try it out!")
        api_key = st.text_input("Enter your OpenAI API Key:", type="password")

    if not validate_openai_api_key(api_key):
        return

    os.environ["OPENAI_API_KEY"] = api_key

    # Imported after the key is set so a visitor who never enters one does not
    # pay for a database connection or an embedding model load.
    from src.llm import pipeline

    query = st.text_input("Enter your card search query:")

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
            with st.spinner("Searching the card pool..."):
                result = asyncio.run(
                    pipeline(query, seed_oracle_id=oracle_id)
                )
            _clear_picker_state()
            if result.text:
                st.markdown(result.text)
        return

    if query:
        with st.spinner("Searching the card pool..."):
            result = asyncio.run(pipeline(query))

        if result.status == "need_pick":
            st.session_state["pending_pick"] = result.choices or []
            st.session_state["pending_query"] = query
            st.session_state["pending_name"] = result.name
            st.session_state["pending_pick_kind"] = result.pick_kind
            st.rerun()
        elif result.text:
            st.markdown(result.text)


if __name__ == "__main__":
    run()
