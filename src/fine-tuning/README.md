# Fine-Tuning & Retrieval-Augmented Generation (RAG) Exploration [WIP]

This directory is part of a broader project to explore how to improve the knowledge and reasoning capabilities of large language models (LLMs) in domains where:
- Datasets are small or specialized
- Semantics and definitions are domain-specific or non-trivial
- Standard RAG approaches often fail to retrieve or synthesize the right information
- Fine-tuning is possible, but not always practical or effective

## Project Purpose
The goal is to investigate methods for enhancing LLM performance on tasks that require more than just surface-level retrieval or naive fine-tuning. In particular, we focus on cases where:
- The knowledge required is salient but not always explicit in the data
- There is implied or contextual knowledge that is hard for LLMs to infer
- Even with RAG, the model may not return the correct or most useful information

### Example Use Case
A toy example in this repo is searching for "cards that ramp lands" in a Magic: The Gathering dataset. Out-of-the-box, LLMs and RAG pipelines tend to return just lands, missing the nuance that "ramp" refers to cards that help you get more lands into play. The challenge is to:
- Engineer features, prompts, or retrieval strategies that surface the right cards
- Explore if and how fine-tuning on small, high-quality datasets can help
- Experiment with hybrid or alternative approaches

## Status
- The initial code here is primarily RAG-focused, but is structured to allow for fine-tuning experiments as well.
- The repo is a work in progress and intended for research and prototyping.

---

## 🚦 Running the Demo App

To launch the fine-tuning demo app, run:

```
streamlit run app.py
```

from this directory.

