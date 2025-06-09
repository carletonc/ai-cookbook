# Magic The Gathering Card Search and Recommendation Engine [WIP]

This project demonstrates a phased approach to building an intelligent card search and recommendation system for Magic: The Gathering. It explores the combination of vector similarity search, large language models (LLMs), and domain-specific knowledge in a specialized context where traditional search methods often fall short.

## Project Purpose
- **Domain:** Magic: The Gathering (MTG) cards, rules, and community knowledge
- **Goal:** Create an intelligent search system that understands both the technical and cultural aspects of MTG
- **Motivation:** Bridge the gap between literal card text and the rich, nuanced understanding that experienced players possess

## Development Phases

### Phase 1: Semantic Card Search (Current)
- Build a robust vector database of MTG cards using ChromaDB
- Implement semantic search capabilities to find cards based on natural language queries
- Focus on proper embedding and retrieval of card characteristics
- Establish filtering and ranking mechanisms for search results

### Phase 2: LLM-Enhanced Recommendations
- Integrate an LLM to interpret user queries and manage search parameters
- Develop intelligent filtering strategies based on game context
- Enable more natural interaction with the card database
- Create a system that can explain its recommendations

### Phase 3: Rules and Context Integration
- Incorporate comprehensive rules knowledge
- Add keyword definitions and mechanics explanations
- Integrate community terminology and slang
- Bridge formal rules with informal player knowledge
- Enable the system to understand and explain card interactions

### Phase 4: Model Optimization (If Viable)
- Evaluate the necessity and feasibility of fine-tuning
- Consider dataset size limitations and alternatives
- Potentially explore few-shot learning approaches
- Focus on preserving accuracy while expanding capabilities

## Current Implementation

### Data Sources
- `data/AtomicCards.json`: Comprehensive MTG card database
- `data/MagicCompRules_21031101.txt`: Official rules text
- `data/chroma_db/`: Vector embeddings and search index
- **Planned:**
  - Keyword and mechanics glossary
  - Community terminology dictionary
  - Common card interactions database

### Features (Phase 1)
- Semantic search across card characteristics
- Natural language query interpretation
- Filtered search by card attributes
- Similarity scoring for results
- Interactive result exploration

### Technical Stack
- ChromaDB for vector storage and retrieval
- OpenAI embeddings for semantic understanding
- Streamlit for interactive interface
- LangChain for LLM integration (Phase 2)

---

## 🚦 Running the Demo

Launch the Streamlit app:
```
streamlit run app.py
```

## Future Milestones

### Phase 2
- [ ] LLM integration for query interpretation
- [ ] Context-aware filtering strategies
- [ ] Explanation generation for recommendations
- [ ] Interactive refinement of searches

### Phase 3
- [ ] Rules knowledge integration
- [ ] Keyword and mechanics database
- [ ] Slang and terminology mapping
- [ ] Card interaction understanding

### Phase 4 (If Viable)
- [ ] Evaluate fine-tuning feasibility
- [ ] Explore few-shot learning options
- [ ] Test hybrid approaches
- [ ] Measure knowledge retention

---

## Project Significance

This project serves as a case study in building intelligent search systems for specialized domains. It demonstrates how to combine vector search, LLMs, and domain knowledge in a way that respects both technical accuracy and community understanding. The phased approach ensures a solid foundation before adding complexity, while keeping the focus on practical utility for users.
