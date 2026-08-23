import asyncio
import os

import streamlit as st

from src.ui.main import validate_openai_api_key


def run():
    st.set_page_config(page_title="AI MTG Card Search & Rec", layout="wide")
    st.title("🧙‍♂️ AI Magic: The Gathering Card Search")

    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    with open(readme_path, "r") as f:
        readme_content = f.read()

    with st.expander("ℹ️&nbsp;&nbsp;About this app", expanded=True):
        st.markdown(readme_content, unsafe_allow_html=True)

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
    if query:
        with st.spinner("Searching the card pool..."):
            response = asyncio.run(pipeline(query))
        st.markdown(response)


if __name__ == "__main__":
    run()
