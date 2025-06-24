# Agent Demo 🤖

A Streamlit-based demo of multi-turn conversational agents powered by LangChain, with context memory and tool integration.

## Features

- **ReAct Agent**: Primary agent using the ReAct (Reason+Act) framework for step-by-step reasoning and tool use.
- **Chain-of-Thought Calculator Tool**: Specialized agent for math problems, demonstrating chain-of-thought prompting.
- **Integrated Tools**:
  - DuckDuckGo Web Search
  - Wikipedia Lookup
  - Calculator
- **Session Memory**: Maintains chat history and context for multi-turn conversations.
- **Configurable**: Choose model, temperature, and memory settings from the sidebar.

## How to Run

1. Install requirements:
   ```
   pip install -r requirements.txt
   ```
2. Launch the app:
   ```
   streamlit run app.py
   ```
3. Enter your OpenAI API key in the sidebar when prompted.

---

This template can be further customized as you add new agents or tools.
