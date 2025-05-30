"""
Simple LLM Agent Demo Application

This is a simplified version of the chat application that demonstrates basic LangChain agent functionality.
It provides a single-turn interaction model without conversation history or context management.
Use this as a starting point for understanding agent implementation, then see chat_app.py for the full featured version.
"""
import os
import streamlit as st
from langchain.agents import AgentExecutor, create_react_agent
# OpenAI expects a plain string and returns a plain string, 
# uses v1/completions and models such as `text-davinci-003`
# ChatOpenAI expects a plain string and returns a plain string, 
# uses v1/chat/completions and models such as `gpt-4.1-mini`
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from pydantic import SecretStr

from constants import HEADER, DESCRIPTION, SYSTEM_PROMPT
from tools import tools

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MODEL = "gpt-4.1-mini"

# Page configuration
st.set_page_config(page_title="Simple LLM Agent Demo", layout="wide")
st.title("🤖 Simple LLM Agent")

# Sidebar for API key
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    os.environ["OPENAI_API_KEY"] = api_key
    
    # Add model selection
    model_options = ["gpt-4.1-mini", "gpt-3.5-turbo"]
    selected_model = st.selectbox("Select Model:", model_options, index=0)
    
    # Add temperature control
    temperature = st.slider("Temperature:", min_value=0.0, max_value=1.0, value=0.3, step=0.1)
    
    st.markdown("### Current System Prompt:")
    st.info(SYSTEM_PROMPT)

# Main content area
st.header(HEADER)
st.markdown(DESCRIPTION)

# Only proceed if API key is provided
if api_key:    
    # Agent prompt
    agent_prompt = PromptTemplate(
        # System prompt variables
        input_variables=["input", "tool_names"], 
        template=SYSTEM_PROMPT 
    )

    # Create the agent with proper typing for API key
    llm = OpenAI(
        api_key=SecretStr(os.environ["OPENAI_API_KEY"]), 
        model=selected_model,
        temperature=temperature
    )
    agent = create_react_agent(llm, tools, agent_prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
    
    # Chat interface
    user_input = st.text_input("What would you like to know?")
    
    if user_input and st.button("Run Agent"):
        with st.spinner("Agent is working..."):
            try:
                # Execute the agent
                response = agent_executor.invoke(
                    {"input": user_input, "tool_names": ", ".join([tool.name for tool in tools])} #, "agent_scratchpad": ""}
                    )
                
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