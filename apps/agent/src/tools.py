from langchain_openai import OpenAI 
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper



# Web search tool
search = DuckDuckGoSearchRun()
search_tool = Tool(
    name="Web Search",
    func=search.run,
    description="""
    Useful for searching the web for current events or specific information. 
    Input should be a search query.
    """
)

# Wikipedia tool
wikipedia = WikipediaAPIWrapper()
wikipedia_tool = Tool(
    name="Wikipedia",
    func=wikipedia.run,
    description="""
    Useful for searching Wikipedia for detailed background information on a topic. 
    Input should be a search query.
    """
)

# Calculator tool
def create_calculator_chain():
    """Create and return the calculator chain with proper API key handling"""
    calculator_template = """
    You are a calculator. You can solve math problems.
    The problem is: {query}
    Think step by step until you reach the final answer.
    Your final response should be the answer to the math problem, without any additional text.
    """
    calculator_prompt = PromptTemplate(template=calculator_template, input_variables=["query"])
    calculator_llm = OpenAI(
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