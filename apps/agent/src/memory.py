import streamlit as st

def initialize_session_memory():
    """Initialize session state for chat history if not already set."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
def append_assistant_response(response: str) -> None:
    """Append the assistant's response to the chat history."""
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response
    })
    
def update_memory_history(user_input: str) -> str:
    """Add user message to chat history and return formatted chat history string."""
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    # Format chat history for context
    if len(st.session_state.messages[:-1]) > 1:
        chat_history = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in st.session_state.messages[:-1][-st.session_state['memory_limit']:]
        ])
    else:
        chat_history = "No history available."
    return chat_history
        
def rollback_last_user_message():
    """Remove the last user message from the chat history if it exists."""
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        st.session_state.messages.pop()
        
def display_chat_history():
    """Display the chat history in the Streamlit app."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        
def initialize_conversation_management_buttons():
    """Display Clear Chat and Export Chat buttons for conversation management."""
    if st.session_state.messages:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Clear Chat"):
                st.session_state.messages = []
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