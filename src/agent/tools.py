"""
LangChain Agent Tools

This module defines the tools available to the LangChain agent:
1. Web Search - Uses DuckDuckGo for current information
2. Wikipedia - Retrieves detailed background information
3. Calculator - Uses LLM for step-by-step math problem solving

Each tool is implemented as a LangChain Tool with a specific description and function.
"""
import os
from langchain_openai import OpenAI 
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from pydantic import SecretStr

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Tool 1: Web search
search = DuckDuckGoSearchRun()
search_tool = Tool(
    name="Web Search",
    func=search.run,
    description="""
    Useful for searching the web for current events or specific information. 
    Input should be a search query.
    """
)

# Tool 2: Wikipedia
wikipedia = WikipediaAPIWrapper()
wikipedia_tool = Tool(
    name="Wikipedia",
    func=wikipedia.run,
    description="""
    Useful for searching Wikipedia for detailed background information on a topic. 
    Input should be a search query.
    """
)

# Tool 3: Calculator via LLM
def create_calculator_chain():
    """Create and return the calculator chain with proper API key handling"""
    calculator_template = """
    You are a calculator. You can solve math problems.
    The problem is: {query}
    Solve this step by step until you reach the final answer.
    """
    calculator_prompt = PromptTemplate(template=calculator_template, input_variables=["query"])
    api_key_str = os.environ.get("OPENAI_API_KEY")
    calculator_llm = OpenAI(
        api_key=SecretStr(api_key_str) if api_key_str else None,
        temperature=0
    )
    return calculator_prompt | calculator_llm

def calculator_handler(tool_input: str) -> str:
    """Handle calculator tool requests with proper input parameter name"""
    calculator_chain = create_calculator_chain()
    return calculator_chain.invoke({"query": tool_input})

calculator_tool = Tool(
    name="Calculator",
    func=calculator_handler,
    description="""
    Useful for solving math problems. Input should be a math problem.
    """
)

# Define the tools list
tools = [search_tool, wikipedia_tool, calculator_tool]