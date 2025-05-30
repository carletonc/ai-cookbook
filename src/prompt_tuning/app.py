# Prompt Tuning & Evaluation Streamlit App
# -----------------------------------------
# This app demonstrates iterative prompt tuning using LLM-as-a-judge evaluation loops.
# It displays the initial prompt, evaluation prompts, and tuning prompt, and allows you to run the tuning loop interactively.

import os
import json
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI, ChatOpenAI
from langchain.chains import LLMChain
import streamlit as st

from prompts import (
    STARTING_PROMPT,
    FACTUALNESS_AND_ACCURACY,
    COHERENCE_AND_STRUCTURE,
    CONCISENESS_AND_INFORMATION_EFFICIENCY,
    FORMAT_COMPLIANCE,
    HALLUCINATION_AND_SOURCE_VALIDITY,
    TUNING_PROMPT
)

# Example tabular data for prompt context
dummy_data = """
    Quarter,Revenue ($M),Profit Margin (%),Customer Satisfaction (%),Enterprise Growth (%),Consumer Growth (%)
    Q1 2024,4.1,12.5,85,38,-8
    Q2 2024,4.3,13.1,87,41,-5
    Q3 2024,5.18,15.3,72,45,-12
    """

# List of evaluation prompts (dimensions)
EVALS = [
    FACTUALNESS_AND_ACCURACY,
    COHERENCE_AND_STRUCTURE,
    CONCISENESS_AND_INFORMATION_EFFICIENCY,
    FORMAT_COMPLIANCE,
    HALLUCINATION_AND_SOURCE_VALIDITY
]
min_score = len(EVALS) * 1
max_score = len(EVALS) * 5
epochs = 10  # Maximum number of tuning iterations

# --- LLM Query Helper ---
def query_llm(prompt: str, params: dict) -> str:
    """
    Query the LLM with a prompt and parameters.
    Returns a string output (handles str or list from LLM response).
    """
    prompt_template = PromptTemplate(
        template=prompt,
        input_variables=list(params.keys())
    )
    chain = prompt_template | LLM
    result = chain.invoke(params).content
    if isinstance(result, str):
        return result
    elif isinstance(result, list):
        return "\n".join(str(x) for x in result)
    else:
        return str(result)



# --- Streamlit UI ---
st.title("Prompt Tuning Demo")

# Sidebar for API key
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")

# Only proceed if API key is provided
if api_key:
    
    # Initialize the language model (OpenAI GPT-4 mini, deterministic)
    LLM = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0.0
    )

    # Show the initial prompt in an expandable section
    with st.expander("Show Dummy Data"):
        st.code(dummy_data)

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

    # --- Main Tuning Loop ---
    if st.button("Run Tuning Loop"):
        prompt = STARTING_PROMPT
        
        history = []  # Store each tuning step for review
        
        for epoch in range(epochs):
            st.markdown(f"### Epoch {epoch+1}")
            
            # Generate LLM output for the current prompt
            output = query_llm(prompt, {"data": dummy_data})
            
            # Prepare evaluation input
            eval_params = {
                "input_prompt_and_data": prompt.format(data=dummy_data),
                "output": output
            }
            
            # Evaluate output on all dimensions
            evals = [[e, query_llm(e, eval_params)] for e in EVALS]
            scores = [json.loads(e[1]) for e in evals]
            
            # Format evaluation results for the tuning prompt
            eval_string = "\n\n".join([
                f"## EVAL PROMPT {i+1}:\n{e[0]}\n## EVAL OUTPUT:\n{e[1]}" for i, e in enumerate(evals)
            ])
            eval_string = eval_string #.format(**eval_params)
            #st.write(eval_string)
            
            # Prepare input for the tuning prompt
            tuning_prompt_dict = {
                "input_prompt": prompt,
                "data": dummy_data,
                "llm_output": output,
                "llm_evaluations": eval_string
            }
            
            # Get tuning suggestion from LLM
            tuning_output = query_llm(TUNING_PROMPT, tuning_prompt_dict)
            st.markdown("**Tuning Output:**")
            st.code(tuning_output)
            tuning_json = json.loads(tuning_output)
            history.append(tuning_json)
            
            # Stop if the tuning rationale says no changes are needed
            if "no changes are needed" in tuning_json.get("rationale", "").lower():
                st.success("Stopping criteria met: No changes are needed.")
                break
            
            # Use the new prompt for the next iteration
            prompt = tuning_json["new_prompt"]
            
        # Show the full tuning history at the end
        st.markdown("---")
        st.markdown("#### Tuning History")
        for i, h in enumerate(history):
            st.markdown(f"**Step {i+1}:**")
            st.json(h)