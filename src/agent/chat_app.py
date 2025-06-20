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
    """Create and return an agent executor for multi-turn LLM agent."""
    agent_prompt = PromptTemplate(
        input_variables=["input", "tool_names", "chat_history"], 
        template=SYSTEM_PROMPT + "\nPrevious conversation:\n{chat_history}\n"
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

def update_context(user_input: str, response: str) -> None:
    """Update conversation context with new user input and agent response."""
    st.session_state.conversation_context["topics"].add(user_input[:50])
    st.session_state.conversation_context["last_input"] = user_input
    st.session_state.conversation_context["agent_memory"].append({
        "input": user_input,
        "response": response
    })

def initialize_session_state():
    """Initialize session state for chat history and context if not already set."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_context" not in st.session_state:
        st.session_state.conversation_context = {
            "topics": set(),
            "last_input": None,
            "agent_memory": []
        }

# Page configuration
st.set_page_config(page_title="Multi-turn LLM Agent Demo", layout="wide")
st.title("🤖 Multi-turn LLM Agent")

with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")

# Main content area
st.header(HEADER)
st.markdown(DESCRIPTION)

# Initialize session state for chat history and context
initialize_session_state()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Only proceed if API key is provided
if validate_openai_api_key(api_key): 
    os.environ["OPENAI_API_KEY"] = api_key
    
    sidebar = init_sidebar()
    agent_executor = get_agent()
    # Chat interface
    user_input = st.chat_input("What would you like to know?")
    
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Format chat history for context
        chat_history = "No history available."
        if len(st.session_state.messages[:-1]) > 1:
            chat_history = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in st.session_state.messages[:-1][-sidebar['memory_limit']:]
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