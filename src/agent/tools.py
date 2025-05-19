import os
from langchain_openai import OpenAI 
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper

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
calculator_template = """
You are a calculator. You can solve math problems.
The problem is: {query}
Solve this step by step.
"""
calculator_prompt = PromptTemplate(template=calculator_template, input_variables=["query"])
calculator_llm = OpenAI(api_key=OPENAI_API_KEY, temperature=0) # model=MODEL, 
calculator_chain = calculator_prompt | calculator_llm # LLMChain(llm=calculator_llm, prompt=calculator_prompt) 
calculator_tool = Tool(
    name="Calculator",
    func=calculator_chain.run,
    description="""
    Useful for solving math problems. Input should be a math problem.
    """
)

# Define the tools list
tools = [search_tool, wikipedia_tool, calculator_tool]