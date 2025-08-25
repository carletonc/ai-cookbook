from pathlib import Path
from typing import Dict
import json

from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from dotenv import load_dotenv

from src.search import retrieve_by_name, retrieve_by_text, HEADER
load_dotenv() 

SCRIPT_DIR = Path(__file__).parent.resolve()
PROMPTS_DIR = SCRIPT_DIR / "prompts"
PLANNER_PATH = PROMPTS_DIR / "planner.md"
RANKER_PATH = PROMPTS_DIR / "ranker.md"

MODEL = "gpt-4.1-nano" # "gpt-4.1-mini", "gpt-3.5-turbo"



def load_prompt(filepath):
    """Loads the content of a Markdown file as plain text."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return None


def query_planner(user_input: str) -> dict:
    llm = ChatOpenAI(
        model=MODEL, 
        temperature=0.1, 
    )
    agent_prompt = PromptTemplate(
        input_variables=['query'], 
        template=load_prompt(PLANNER_PATH) 
    )
    chain = agent_prompt | llm
    output = chain.invoke({'query':user_input})
    return json.loads(output.content)


def rank_and_explainer(user_input: str, context: str) -> str:
    llm = ChatOpenAI(
        model=MODEL, 
        temperature=0.1, 
    )
    agent_prompt = PromptTemplate(
        input_variables=['query', 'context'], 
        template=load_prompt(RANKER_PATH) 
    )
    chain = agent_prompt | llm
    output = chain.invoke({'query':user_input, 'context':context})
    return output.content


def pipeline(input_query: str) -> Dict:
    """ """
    
    planner_output = query_planner(input_query)
    
    target_card_text = None
    candidates = []
    
    if planner_output["query_type"] == "seed_card":
        #print('Seed Card was reached')
        
        target_card_text = retrieve_by_name(planner_output["card_name"])
        for t in target_card_text['text'].split('\t'):
            cards = retrieve_by_text(t)
            for c in cards:
                if c not in candidates:
                    candidates.append(c)
                    
        target_card_text = "\n\nTarget Card Context:\n" + HEADER + '|'.join([str(c) for c in target_card_text])
        
    elif planner_output["query_type"] == "text_search":
        #print('Text search was reached')
        
        cards = retrieve_by_text(planner_output["search_text"])
        for c in cards:
            if c not in candidates:
                candidates.append(c)
        
        
    elif planner_output["query_type"] == "unsupported":
        output = f"`{input_query}` is unsupported, so we cannot generated meaningful recommendations for you.\nTry searching for a card by its textual description or by a card name you want to find."
        return output
    
    
    else:
        output = f"`{input_query}` an unknown error occured, please try again so we can generate meaningful recommendations.\nTry searching for a card by its textual description or by a card name you want to find."
        return output
    
    if candidates:
        
        if target_card_text:
            input_query += target_card_text
        context = '\n'.join(['|'.join([str(c) for c in candidate]) for candidate in candidates])
        context = HEADER + context
        ranker_output = rank_and_explainer(user_input=input_query, context=context)
        return ranker_output


if __name__ == "__main__":
    for q in [' Control opponents turns', "Return cards to hand", "Cards similar to Chatterfang", ]:
        output = pipeline(q)
        print(f'Input Query: {q}\n'
              f'Output:\n{output}\n')
        print('---\n')