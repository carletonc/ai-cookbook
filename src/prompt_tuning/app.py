import os
import json
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI, ChatOpenAI
from langchain.chains import LLMChain

from prompts import (
    STARTING_PROMPT,
    FACTUALNESS_AND_ACCURACY,
    COHERENCE_AND_STRUCTURE,
    CONCISENESS_AND_INFORMATION_EFFICIENCY,
    FORMAT_COMPLIANCE,
    HALLUCINATION_AND_SOURCE_VALIDITY,
    TUNING_PROMPT
)

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DUMMY_DATA = """
    Quarter,Revenue ($M),Profit Margin (%),Customer Satisfaction (%),Enterprise Growth (%),Consumer Growth (%)
    Q1 2024,4.1,12.5,85,38,-8
    Q2 2024,4.3,13.1,87,41,-5
    Q3 2024,5.18,15.3,72,45,-12
    """

# Initialize language model
LLM = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.0
)

EVALS = [FACTUALNESS_AND_ACCURACY, COHERENCE_AND_STRUCTURE, CONCISENESS_AND_INFORMATION_EFFICIENCY, FORMAT_COMPLIANCE, HALLUCINATION_AND_SOURCE_VALIDITY]
min_score = len(EVALS) * 1
max_score = len(EVALS) * 5
epochs = 10
    
def query_llm(prompt: str, params: dict) -> str:
    """
    Simulate a model output based on the provided prompt.
    In a real-world scenario, this function would call an LLM API.
    """
    # Simulate a model response
    prompt_template = PromptTemplate(
        template=prompt,
        input_variables=list(params.keys())
    )
    chain = prompt_template | LLM # LLMChain(llm=LLM, prompt=prompt_template)
    return chain.invoke(params).content

for n in range(epochs):
    print("Starting epoch:\t", n + 1)
    
    # Placeholder, we need to iterate through various data, store outputs, and score across the data
    # such as "Mean Score" and "Std Dev Score" per eval prompt and across all outputs
    # to determine the most performant prompt. 
    
    OUTPUT = query_llm(STARTING_PROMPT, {"data": DUMMY_DATA})
    print('Completed initial llm query')
    
    eval_params = {
        # probably need to replace PromptTemplate here
        "input_prompt_and_data": PromptTemplate(template=STARTING_PROMPT).format(**{"data": DUMMY_DATA}),
        "output": OUTPUT
    }
    print('Starting eval...')
    evals = [[e, query_llm(e, eval_params)] for e in EVALS]
    print('...completed.')
    #[print(e) for e in evals]
    scores = [json.loads(e[1]) for e in evals]
    eval_string = "\n\n".join(["## EVAL PROMPT "+str(i+1)+":"+str(e[0])+"\n## EVAL OUTPUT:\n\\{"+e[1]+"}\\" for i, e in enumerate(evals)])
    eval_string = PromptTemplate(template=eval_string).format(**eval_params)
        
    tuning_prompt_dict = {
        "input_prompt": STARTING_PROMPT, 
        "data": DUMMY_DATA, 
        "llm_output": OUTPUT, 
        "llm_evaluations": eval_string 
    }
    tuning_output = query_llm(TUNING_PROMPT, tuning_prompt_dict) 
    print(tuning_output)
    tuning_output = json.loads(tuning_output)
    STARTING_PROMPT = tuning_output["new_prompt"]
    print(STARTING_PROMPT)
    
    # placeholder to store outputs in MLFlow or Database
    # perhaps we need to refine the LLM evals to maximize mean score and minimize std dev score
    