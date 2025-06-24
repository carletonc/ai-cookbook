import os
import json
from langchain_openai import OpenAI, ChatOpenAI
from langchain.chains import LLMChain
import streamlit as st

from src.constants import DESCRIPTION, DUMMY_DATA
from src.utils import validate_openai_api_key, query_llm, reveal_prompts, EVALS
from src.prompts import STARTING_PROMPT, TUNING_PROMPT



min_score = len(EVALS) * 1
max_score = len(EVALS) * 5
epochs = 10  # Maximum number of tuning iterations

# --- Streamlit UI ---
st.set_page_config(page_title="Automated Prompt Tuning Template", layout="wide")
st.title("Prompt Tuning Template Demo")
st.warning("NOTICE: This is a template intended to be adapted for external use cases, and may be prone to errors as a result of not have a true dataset to fine-tune on.")
st.markdown(DESCRIPTION)

# Sidebar for API key
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    os.environ["OPENAI_API_KEY"] = api_key

# Only proceed if API key is provided
if validate_openai_api_key(api_key):
    reveal_prompts()

    # --- Main Tuning Loop ---
    if st.button("Run Tuning Loop"):
        prompt = STARTING_PROMPT
        
        history = []  # Store each tuning step for review
        
        for epoch in range(epochs):
            st.markdown(f"### Epoch {epoch+1}")
            
            # Generate LLM output for the current prompt
            output = query_llm(prompt, {"data": DUMMY_DATA})
            
            # Prepare evaluation input
            eval_params = {
                "input_prompt_and_data": prompt.format(data=DUMMY_DATA),
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
                "data": DUMMY_DATA,
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