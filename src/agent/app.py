import os
import streamlit as st

from utils.constants import HEADER, DESCRIPTION, SYSTEM_PROMPT
from utils.tools import tools
from utils.llm import validate_openai_api_key, initialize_sidebar, get_agent
from utils.memory import (
    initialize_session_memory, 
    append_assistant_response, 
    update_memory_history, 
    rollback_last_user_message, 
    display_chat_history, 
    initialize_conversation_management_buttons
)



# Page configuration
st.set_page_config(page_title="Chat Agent Demo", layout="wide")
st.title("🤖 Chat Agent")

with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")

# Main content area
st.header(HEADER)
st.markdown(DESCRIPTION)

# Only proceed if API key is provided
if validate_openai_api_key(api_key): 
    os.environ["OPENAI_API_KEY"] = api_key
    
    initialize_sidebar()
    agent_executor = get_agent(tools)
    
    # Initialize session state for chat history and context
    initialize_session_memory()
    
    # Chat interface
    if user_input := st.chat_input("What would you like to know?"): 
        chat_history = update_memory_history(user_input)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
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
                    append_assistant_response(response["output"])
                    
                    # Show thought process in expander
                    with st.expander("View agent's thought process"):
                        st.json(response)
                
                except Exception as e:
                    # PLACEHOLDER - need to replace rollback logic with agent retry logic here
                    rollback_last_user_message()
                    st.error(f"An error occurred: {str(e)}")
    else:    
        display_chat_history()

    initialize_conversation_management_buttons()
        
else:
    st.warning("Please enter your OpenAI API key in the sidebar to use the agent.")