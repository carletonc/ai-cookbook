import streamlit as st

def initialize_session_memory():
    """Initialize session state for chat history and context if not already set."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_context" not in st.session_state:
        st.session_state.conversation_context = {
            "topics": set(),
            "last_input": None,
            "agent_memory": []
        }

def update_context(user_input: str, response: str) -> None:
    """Update conversation context with new user input and agent response."""
    st.session_state.conversation_context["topics"].add(user_input[:50])
    st.session_state.conversation_context["last_input"] = user_input
    st.session_state.conversation_context["agent_memory"].append({
        "input": user_input,
        "response": response
    })
    
def append_assistant_response(response: str) -> None:
    """Append the assistant's response to the chat history."""
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response
    })
    
def update_memory_history(user_input: str, memory_limit: int) -> str:
            """Add user message to chat history and return formatted chat history string."""
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            # Format chat history for context
            if len(st.session_state.messages[:-1]) > 1:
                chat_history = "\n".join([
                    f"{msg['role'].upper()}: {msg['content']}"
                    for msg in st.session_state.messages[:-1][-memory_limit:]
                ])
            else:
                chat_history = "No history available."
            return chat_history
        
def initialize_conversation_management_buttons():
        """Display Clear Chat and Export Chat buttons for conversation management."""
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