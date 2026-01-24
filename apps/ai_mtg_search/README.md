# Agentic Search Engine for Magic: The Gathering Cards

## The Problem

Imagine searching for "treatments that prevent clotting." The search engine returns vascular filters, hydration protocols, and blood type screening - all technically correct, but representing completely different medical mechanisms. You meant anticoagulant drugs specifically. The search understood your *words* but missed your *intent*.

Now the inverse: you need warfarin, but it costs $300/month. You need a functionally equivalent generic at a fraction of the cost. The search engine can't help - it doesn't understand drug mechanisms well enough to identify functional equivalents or optimize for cost while maintaining efficacy.

Finally: doctors use informal shorthand like "cath lab" that never appears in official documentation. Search using this terminology and the system fails - the language doesn't exist in its training data.

**This is the three-layer semantic problem**: common words with strict technical definitions, undocumented expert slang, and queries requiring multi-step reasoning. It appears across technical domains - legal research, patent search, technical support.

**Magic: The Gathering faces this exact problem**, with an added market failure: the best cards are prohibitively expensive ($20-$500+), and popularity-driven recommendations make every deck identical.

---

## Magic: the Gathering as a Case Study

Magic is a competitive card game with 33,000+ cards. A player wants: *"Budget alternatives to Rhystic Study that draw cards when opponents do things."*

This breaks standard search across three layers:

### Layer 1: Technical Language Override

**"Destroy target creature"** seems simple, but:
- "Destroy" is a specific game action
- Some creatures are "indestructible" (immune to destruction)
- Creatures can be "exiled" instead (different game zone, different triggers)
- Creatures can be reduced to 0 toughness (bypasses indestructible)

**LLMs learn "destroy" and "exile" are semantically similar** (both involve removal). But functionally, they're as different as prescribing antibiotics versus performing surgery - different mechanisms, different edge cases, different deck implications.

*Similar to legal "consideration" or medical "acute" - common words repurposed with narrow technical meanings.*

### Layer 2: Undocumented Slang

Players use terminology evolved over 30+ years that never appears in official card text:
- **"Impulse draw"**: Exile cards temporarily *(contradicts literal meaning - not drawing!)*
- **"Mana rock"**: Artifact that produces mana
- **"Ramp"**: Accelerate mana production
- **"Board wipe"**: Destroy all creatures

This exists in Reddit discussions and tournament commentary, not official rules. Standard vector search fails because this terminology isn't in training data or appears in wrong contexts.

### Layer 3: Multi-Hop Reasoning

*"Things that stop flying creatures"* must map to:
- Creatures with "Reach" keyword *(can block flyers)*
- Removal spells *(destroy/exile the creature)*
- Ability removal *(strip flying from creature)*
- Global effects *("creatures lose all abilities")*

Each has different card text patterns. The system must reason: **game rules → solution categories → text variations**.

### Why Vector Search Fails

Query: *"Budget alternatives to Rhystic Study"* requires:
1. Current market price lookup ($40)
2. Understand mechanics (draw when opponents cast spells + tax)
3. Decompose into searchable components
4. Find cards sharing *subset* of mechanics
5. Filter by price (<$10) and color identity
6. Rank by functional similarity + budget savings

Vector search returns text-similar cards. **It cannot access pricing data, decompose mechanics, or execute multi-objective optimization.**

---

## The Market Problem

### Economic Barrier
Competitive decks cost $500-$2000. Staple cards run $20-$500+. Budget players are priced out.

**The insight**: Functionally equivalent cards from unpopular sets often cost <$5, but existing tools can't surface them.

**Example:**
- **Rhystic Study** ($40): Draw when opponent casts spell (unless they pay 1)
- **Insight** ($0.25): Draw when opponent casts green spell
- **Monastery Siege** ($0.50): Draw each turn (or mill opponent)

In specific contexts, these achieve 60-80% of Rhystic Study's function at <2% the cost. **Existing tools optimize for popularity, not functional similarity + budget.**

### Homogenization
Recommendation engines rank by popularity, creating feedback loops. Result: every deck uses the same 50-100 staples. 

Players want mechanically viable cards their opponents haven't seen - while staying within budget.

---

## Why This Is Hard

Magic is an ideal testbed because:
- 33,000+ cards with well-defined rules (250-page rulebook)
- Clear success metrics (deck functionality, cost efficiency, novelty)
- Real user pain points (economic barriers + homogenization)

**Standard NLP fails because:**
1. **Technical vocabulary override**: Common words with contradictory game-mechanical definitions
2. **Undocumented slang**: 30+ years of evolved terminology not in training data
3. **Multi-hop reasoning**: Queries need intent → mechanics → retrieval chains
4. **Multi-objective constraints**: Optimize for relevance AND budget AND novelty simultaneously

---

## Technical Solution: Agentic Workflow Design

### Why This Project Matters

This is a living project, primarily intended as an **exercise in agentic workflow design** - architecting multi-stage systems that combine LLM reasoning with structured validation.

**The domain (Magic) provides ideal conditions:**
- Clear ground truth for evaluation (functional card equivalence validated by expert players)
- Measurable success metrics (precision, budget efficiency, novelty)
- Real user impact (economic accessibility, deck diversity)

Future expansions may include memory for personalization, traceability for debugging complex queries, and production-grade reliability features - but the current focus is on designing effective reasoning workflows.

### Current Approach: Deterministic Multi-Stage Pipeline

The system uses a **single-turn agentic workflow** designed to maintain reproducible outputs. Each query flows through discrete stages:

**Stage 1: Query Understanding & Translation**
- Parse user intent and identify slang terms
- Translate informal language → formal game mechanics using prompt engineering
- *Example: "mana rocks under 2 CMC" → "artifacts with mana abilities where converted mana cost ≤ 2"*

**Stage 2: Hybrid Retrieval**
- **Vector search**: Semantic similarity using embeddings (broad recall)
- **Structured filtering**: Color identity, card type, mana cost constraints
- **Rules validation**: Mechanical correctness (does this card actually work in this deck?)

**Stage 3: Multi-Objective Ranking**

Score retrieved cards on weighted criteria:
- **Semantic relevance** (primary): How well does it match functional intent?
- **Budget efficiency** (secondary): Price relative to "obvious" staple alternatives
- **Novelty** (tertiary): Penalize cards in top-100 most-played lists
- **Legality** (filter): Deprioritize illegal cards but still surface if search-relevant

*Each stage is deterministic - same query produces identical results, enabling systematic evaluation and iteration.*

### Alternatives Under Consideration

**Agentic loops with iterative refinement:**
- Initial retrieval → evaluate precision → reformulate query if needed → re-retrieve
- Enables self-correction when slang is misinterpreted or initial results miss the mark
- *Trade-off: Non-deterministic outputs, harder to debug, increased latency & cost*

**Fine-tuning for domain knowledge:**
- Fine-tune embeddings on Magic corpus (comprehensive rules + community discussions + competitive deck lists)
- Learn direct mappings: slang → mechanics, functional similarity despite different text patterns
- *Trade-off: Upfront data engineering cost, but potentially more efficient than complex prompt chains*