from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from pprint import pprint
from dotenv import load_dotenv
load_dotenv() 

from src.utils import get_vector_store

MODEL = "gpt-4.1-nano" # "gpt-4.1-mini", "gpt-3.5-turbo"
TEMPERATURE = 0.5
SYSTEM_PROMPT = """
You are a helpful AI assistant designed to accurately answer questions related to Magic The Gathering (MTG) cards. You will receive an input question and potential cards that are relevant to the question. Your task is to provide an accurate and wholistic answer to the question. You may not need to return all cards or all the related metadata for each card in the context, but you should use the provided context to inform your answer. If the question is not related to MTG cards, you should respond with "I don't know" or "I cannot answer that question."

## Question
{user_input}

## Context
{context}
"""

def get_agent(user_input: str, context: str = "") -> str:
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
    response = chain.run(user_input=user_input, context=context)
    return response

def get_context(
    user_input: str, 
    K: int = 100, 
    feats: list = ['name', 'text', 'type', 'power', 'toughness', 'manaCost', 'colorIdentity', 'legalities.commander']
    ) -> str:
    vectorstore = get_vector_store()
    results = vectorstore.similarity_search_with_score(
        user_input, 
        k=K, 
    )
    
    # filter for results & merge metadata
    context = '|'.join(feats) + '\n' + '\n'.join(
        ['|'.join(
                [result[0].metadata[k] if k in result[0].metadata else '' for k in feats]
            ) for result in results]
        )
    return context
