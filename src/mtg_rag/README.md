# Fine-Tuning & Retrieval-Augmented Generation (RAG) Exploration [WIP]

This directory is part of a broader project to explore how to improve the knowledge and reasoning capabilities of large language models (LLMs) in highly specialized domains—where even web search and standard RAG approaches often fail to retrieve or synthesize the right information.

## Project Purpose
- **Domain:** Magic: The Gathering (MTG) cards and rules
- **Goal:** Enable LLMs to recommend cards and answer questions about MTG using both structured card data (`AtomicCards.json`), the official rules (`MagicCompRules_21031101.txt`), and community knowledge (slang, idioms, and nuanced reasoning).
- **Motivation:** Many domains (like MTG) have complex, evolving, and highly specific rules, slang, and community knowledge that are not well-covered by general web search or public LLM training data. This project aims to bridge that gap and make recommendations that reflect real player experience.

## Approach
- **Phase 1: Retrieval-Augmented Generation (RAG)**
  - Use vector search to retrieve relevant card, rule, and (eventually) community knowledge snippets for a given query.
  - Augment LLM prompts with these retrieved contexts to improve answer and recommendation quality.
  - Evaluate how well RAG alone can help the LLM reason about the domain, including slang and nuanced meanings.
- **Phase 2: Fine-Tuning (Planned/Future)**
  - If RAG alone is insufficient, experiment with fine-tuning an LLM on domain-specific data, QA pairs, and community-sourced examples (including slang and idioms).
  - Compare performance of RAG vs. fine-tuned models, especially for queries involving embedded meanings or non-obvious recommendations.

## Data
- `data/AtomicCards.json`: All MTG cards (structured data)
- `data/MagicCompRules_21031101.txt`: Official MTG comprehensive rules (plain text)
- `data/chroma_db/`: Vector database for fast retrieval (auto-generated)
- **Planned:** Community Q&A, slang glossaries, deck techs, and tournament commentary

## Status
- RAG pipeline and demo app in progress
- Fine-tuning experiments planned for future iterations
- Community knowledge and slang integration planned

---

## 🚦 Running the Demo App

To launch the fine-tuning & RAG demo app, run:

```
streamlit run app.py
```

from this directory.

---

## Future Directions
- Add more domain-specific datasets (e.g., tournament rulings, decklists, community Q&A, slang/idiom glossaries)
- Explore prompt engineering and evaluation strategies for nuanced recommendations
- Implement and benchmark fine-tuning workflows
- Develop robust evaluation metrics for domain-specific QA and recommendations
- Collect and integrate user feedback to improve recommendations

---

## Why This Matters

Many real-world domains require deep, context-specific knowledge—including slang, idioms, and community wisdom—that LLMs cannot learn from the open web or official documentation alone. This project is a testbed for building, evaluating, and fine-tuning LLMs in such settings, with the goal of making recommendations that feel authentic and useful to real players.
