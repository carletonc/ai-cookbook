"""
Multi-turn LLM Agent Chat Application

This module implements a Streamlit-based chat interface for interacting with a LangChain agent.
It supports:
- Multi-turn conversations with context preservation
- Configurable model selection and parameters
- Chat history management and export
- Agent thought process visualization

Key Components:
- LangChain agent with custom tools (from tools.py)
- Streamlit UI with sidebar configuration
- Session state management for conversation context
"""
import os
import streamlit as st
from langchain.agents import AgentExecutor, create_react_agent
# OpenAI expects a plain string and returns a plain string, 
# uses v1/completions and models such as `text-davinci-003`
# ChatOpenAI expects a plain string and returns a plain string, 
# uses v1/chat/completions and models such as `gpt-4.1-mini`
from langchain_openai import OpenAI, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from typing import Dict, List
from pydantic import SecretStr

from constants import HEADER, DESCRIPTION, SYSTEM_PROMPT
from tools import tools

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Page configuration
st.set_page_config(page_title="Multi-turn LLM Agent Demo", layout="wide")
st.title("🤖 Multi-turn LLM Agent")

# Initialize session state for chat history and context
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "conversation_context" not in st.session_state:
    st.session_state.conversation_context = {
        "topics": set(),
        "last_input": None,
        "agent_memory": []
    }

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    os.environ["OPENAI_API_KEY"] = api_key
    
    # Add model selection
    model_options = ["gpt-4.1-mini", "gpt-3.5-turbo"]
    selected_model = st.selectbox("Select Model:", model_options, index=0)
    
    # Add temperature control
    temperature = st.slider("Temperature:", min_value=0.0, max_value=1.0, value=0.3, step=0.1)
    memory_history_limit = st.number_input("Memory Limit:", min_value=1, max_value=100, value=10, step=1)
    
    st.markdown("### Current System Prompt:")
    st.info(SYSTEM_PROMPT)

# Main content area
st.header(HEADER)
st.markdown(DESCRIPTION)

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def update_context(user_input: str, response: str) -> None:
    """Update conversation context with new information"""
    st.session_state.conversation_context["topics"].add(user_input[:50])
    st.session_state.conversation_context["last_input"] = user_input
    st.session_state.conversation_context["agent_memory"].append({
        "input": user_input,
        "response": response
    })

# Only proceed if API key is provided
if api_key:    
    # Agent prompt with context
    agent_prompt = PromptTemplate(
        input_variables=["input", "tool_names", "chat_history"], 
        template=SYSTEM_PROMPT + "\nPrevious conversation:\n{chat_history}\n"
    )

    # Create the agent with proper typing for API key
    api_key_str = os.environ.get("OPENAI_API_KEY")
    llm = ChatOpenAI(
        api_key=SecretStr(api_key_str) if api_key_str else None,
        model=selected_model, 
        temperature=temperature
    )
    agent = create_react_agent(llm, tools, agent_prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
    
    # Chat interface
    user_input = st.chat_input("What would you like to know?")
    
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Format chat history for context
        chat_history = "No history available."
        if len(st.session_state.messages[:-1]) > 1:  # If there are previous messages
            # Only include messages up to but not including the current user message
            chat_history = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in st.session_state.messages[:-1][-memory_history_limit:]
            ])
        
        with st.chat_message("assistant"):
            with st.spinner("Agent is working..."):
                try:
                    # Execute the agent with chat history
                    response = agent_executor.invoke({
                        "input": user_input,
                        "tool_names": ", ".join([tool.name for tool in tools]),
                        "chat_history": chat_history
                    })
                    
                    # Display the response
                    st.markdown(response["output"])
                    
                    # Add assistant's response to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response["output"]
                    })
                    
                    # Update conversation context
                    update_context(user_input, response["output"])
                    
                    # Show thought process in expander
                    with st.expander("View agent's thought process"):
                        st.write(str(response))
                
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

    # Add conversation management buttons
    if st.session_state.messages:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Clear Chat"):
                st.session_state.messages = []
                st.session_state.conversation_context = {
                    "topics": set(),
                    "last_input": None,
                    "agent_memory": []
                }
                st.rerun()
        
        with col2:
            if st.button("Export Chat"):
                chat_text = "\n\n".join([
                    f"{msg['role'].upper()}: {msg['content']}"
                    for msg in st.session_state.messages
                ])
                st.download_button(
                    label="Download Chat History",
                    data=chat_text,
                    file_name="agent_chat_history.txt",
                    mime="text/plain"
                )
else:
    st.warning("Please enter your OpenAI API key in the sidebar to use the agent.")