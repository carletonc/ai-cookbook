# AI Cookbook 🤖

A collection of cool AI tools and examples to play with! Here's what's cooking:

## 🎯 What's Inside

- **MTG Recommender** (`src/mtg_recommender`): Magic: The Gathering card search and recommendation engine using semantic search, vector DB, and LLMs. This is an ongoing experiment in expanding the knowledge of LLMs and agents to capture colloquialisms, slang, and niche definitions that generalized language models often miss -- both generative and embedding models alike. The project explores how to bridge the gap between formal rules and informal player knowledge, and could be extended to fine-tuning a language model for improved embedding extraction in specialized domains.
- **Agent Demo** (`src/agent`): LangChain-based chat agents with context memory & tooling. Currently implements a ReAct agent as the primary model, and a Chain-of-Thought agent for a calculator.
- **Prompt Tuning** (`src/prompt_tuning`): A prompt-tuning template inspired by neural network-style self-learning, leveraging LLM-as-a-Judge for automated evaluation and improvement of prompts. Intended to be modified for other use cases and domains.
- **Error Analysis** (`src/error_analysis`): LLM/ML error analysis tool for annotating, labeling, and analyzing model errors. Soon to supports CSV/JSON export and data-driven insights.

## 🚀 Quick Start

1. Clone the repo
2. Pick a demo to run!

---

**To launch any interactive demo, run:**

```
streamlit run app.py
```

from the appropriate subdirectory (e.g., `src/prompt_tuning`, `src/agent`, etc.).
