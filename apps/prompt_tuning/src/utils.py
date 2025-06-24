import streamlit as st
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI, ChatOpenAI
from langchain.chains import LLMChain

from .constants import DUMMY_DATA
from .prompts import (
    STARTING_PROMPT,
    FACTUALNESS_AND_ACCURACY,
    COHERENCE_AND_STRUCTURE,
    CONCISENESS_AND_INFORMATION_EFFICIENCY,
    FORMAT_COMPLIANCE,
    HALLUCINATION_AND_SOURCE_VALIDITY,
    TUNING_PROMPT
)

# List of evaluation prompts (dimensions)
EVALS = [
    FACTUALNESS_AND_ACCURACY,
    COHERENCE_AND_STRUCTURE,
    CONCISENESS_AND_INFORMATION_EFFICIENCY,
    FORMAT_COMPLIANCE,
    HALLUCINATION_AND_SOURCE_VALIDITY
]

def validate_openai_api_key(api_key):
    """Check if the OpenAI API key is valid. Returns True if valid, False otherwise. Shows a warning in the sidebar if invalid."""
    if not api_key:
        # No key entered yet; do not warn
        return False
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        # Make a minimal call (list models)
        client.models.list()
        return True
    except Exception:
        with st.sidebar:
            st.warning("Invalid OpenAI API key. Please check your key and try again.")
        return False

# --- LLM Query Helper ---
def query_llm(prompt: str, params: dict) -> str:
    """Send a prompt and parameters to the LLM and return the output as a string."""
    prompt_template = PromptTemplate(
        template=prompt,
        input_variables=list(params.keys())
    )
    
    LLM = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0.0
    )
    
    chain = prompt_template | LLM
    result = chain.invoke(params).content
    
    if isinstance(result, str):
        return result
    elif isinstance(result, list):
        return "\n".join(str(x) for x in result)
    else:
        return str(result)
    
def reveal_prompts():
    """Display all prompts and dummy data in expandable sections in the UI."""
    # Show the initial prompt in an expandable section
    with st.expander("Show Dummy Data"):
        st.code(DUMMY_DATA)

    # Show the initial prompt in an expandable section
    with st.expander("Show Initial Prompt"):
        st.code(STARTING_PROMPT)

    # Show all evaluation prompts in an expandable section
    with st.expander("Show Evaluation Prompts"):
        for i, eval_prompt in enumerate(EVALS):
            st.markdown(f"**Eval Prompt {i+1}:**")
            st.code(eval_prompt)
            
    # Show the tuning prompt in an expandable section
    with st.expander("Show Tuning Prompt"):
        st.code(TUNING_PROMPT)
    return