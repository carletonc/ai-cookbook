from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from pprint import pprint
from dotenv import load_dotenv
load_dotenv() 

from src.db.vectorstore import get_vector_store

MODEL = "gpt-4.1-nano" # "gpt-4.1-mini", "gpt-3.5-turbo"
TEMPERATURE = 0.5

SYSTEM_PROMPT = """
You are a helpful AI assistant designed to accurately answer questions related to Magic The Gathering (MTG) cards. You will receive an input question and potential cards that are relevant to the question. Your task is to provide an accurate and wholistic answer to the question. You may not need to return all cards or all the related metadata for each card in the context, but you should use the provided context to inform your answer. If the question is not related to MTG cards, you should respond with "I don't know" or "I cannot answer that question."

## Question
{user_input}

## Context
{context}
"""

NEW_SYSTEM_PROMPT = """
Analyze this Magic: The Gathering search query: {original_query}
        
Return a JSON with:
1. "keywords": List of exact Magic terms to search for
2. "concepts": List of broader concepts/mechanics
3. "card_types": Relevant card types
4. "synonyms": Alternative phrasings

Example for "cards that make zombies stronger":
{{
    "keywords": ["zombie", "+1/+1", "anthem", "lord"],
    "concepts": ["tribal synergy", "creature buffs", "zombie tribal"],
    "card_types": ["creature", "enchantment", "instant", "sorcery"],
    "synonyms": ["zombie lord", "zombie anthem", "undead tribal"]
}}
"""

ROUTER_PROMPT = """
Analyze this Magic: The Gathering search query: {original_query}
        
Return a JSON with:
1. "decision": "get_card_by_name" or "get_cards_by_text" or "execute_multiple_searches"
2. "new_input": "this input should match card target card text"

Example for "cards that make zombies stronger":
{{
    "decision": 
    "new_input": 
}}
"""



def query_llm(user_input: str, context: str = "") -> str:
    """Create and return an agent executor for multi-turn LLM agent."""
    llm = ChatOpenAI(
        model=MODEL, 
        temperature=TEMPERATURE, 
    )
    agent_prompt = PromptTemplate(
        input_variables=['user_input', 'context'], 
        template=SYSTEM_PROMPT 
    )
    chain = LLMChain(llm=llm, prompt=agent_prompt)
    return chain.run(user_input=user_input, context=context)


def router_llm():
    pass


def main(input):
    # start with router -- output structure:
    # {'decision': "get_card_name", "input": "Rhystic Study"}
    
    # if router_output == 'get_card_name':
    #    text = get_text_from_name()
    #    get input(s) for hybrid search
    #    send to llm for analysis
    pass