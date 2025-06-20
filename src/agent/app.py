import os
import streamlit as st
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from constants import HEADER, DESCRIPTION, SYSTEM_PROMPT
from tools import tools
from utils import validate_openai_api_key, init_sidebar

def get_agent():
    agent_prompt = PromptTemplate(
        # System prompt variables
        input_variables=["input", "tool_names"], 
        template=SYSTEM_PROMPT 
    )
    llm = ChatOpenAI(
        model=sidebar['model'],
        temperature=sidebar['temperature']
    )
    agent = create_react_agent(llm, tools, agent_prompt)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        handle_parsing_errors=True
    )
    return agent_executor



# Page configuration
st.set_page_config(page_title="Simple LLM Agent Demo", layout="wide")
st.title("🤖 Simple LLM Agent")

# Main content area
st.header(HEADER)
st.markdown(DESCRIPTION)

# Only proceed if API key is provided
if validate_openai_api_key(api_key): 
    os.environ["OPENAI_API_KEY"] = api_key
    sidebar = init_sidebar()
    
    agent_executor = get_agent()
    
    # Chat interface
    user_input = st.text_input("What would you like to know?")
    
    if user_input and st.button("Run Agent"):
        with st.spinner("Agent is working..."):
            try:
                # Execute the agent
                response = agent_executor.invoke({
                    "input": user_input,
                    "tool_names": ", ".join([tool.name for tool in tools]) 
                    #, "agent_scratchpad": ""
                })
                
                # Display the response
                st.markdown("### Answer")
                st.write(response["output"])
                
                # Display the agent's thought process
                with st.expander("View agent's thought process"):
                    st.write(str(response)) #response["intermediate_steps"])
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
else:
    st.warning("Please enter your OpenAI API key in the sidebar to use the agent.")