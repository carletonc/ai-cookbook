## Motivation

An LLM answers from the average of its training data, and Magic is a small slice of that corpus, so a general-purpose model doesn't know the game's rules — it approximates them, fluently and wrongly. A bigger model doesn't change the mixture, and a model that self-corrects is correcting against the same thin prior without properly engineered context.

Four properties of the domain also break plain semantic search:

1. **Technical vocabulary.** Ordinary words are load-bearing rules terms: a *tutor* searches your library, to *mill* is to move cards from library to graveyard, and *counter* means both cancelling a spell and a myriad of possible marker sitting on a creature. The collisions have mechanical consequences — *destroy*, *exile*, and *sacrifice* all read as "removal," but indestructible stops only the first, exile doesn't count as dying (so death triggers never fire), and sacrifice ignores both. Embeddings put these terms next to each other because English does; the rules pull them apart.
2. **Embedded slang.** *Mana rock*, *board wipe*, and *impulse draw* appear nowhere in official card text or the rulebook, yet they're how players actually search. Some of it inverts the plain meaning: impulse draw isn't drawing at all — it exiles cards to play temporarily, so none of the "whenever you draw" triggers a model would assume actually fire.
3. **One need, many mechanics.** "Stop a flying creature" is served by several unrelated functions — reach, removal, ability-stripping, or a global effect — each with entirely different card text.
4. **One card, many functions.** A single card can be ramp, lifegain, and card draw at once. Embedding it as one document blurs all three into one vector.

What makes that worth solving is the shape of the game itself. The strongest cards are often prohibitively expensive, and the well-known answers are the ones everyone already plays — so players are optimizing for two things at once: spend less, and don't play the same deck as the table next to them. Somewhere in a 33,000+ card legal pool there is usually a cheaper, less-played card that does the job. Finding it is a retrieval and ranking problem that no tool does well (yet).

## Architecture

```
Query → Router (LLM) → Retrieval (vector + fuzzy) → Re-ranker (LLM) → Ranked cards + rationale
```

**1. Router.** An LLM classifies the query into `seed_card` ("alternatives to Rhystic Study"), `text_search` ("draw when opponents cast spells"), or `unsupported`, returning strict JSON. Out-of-scope asks — rules adjudication, price-only, "what commander should I build" — are declined rather than answered badly. The cheapest fix for a hallucination is not answering.

**2. Retrieval.** Card data lives in Neon Postgres with `pgvector`, maintained by a separate weekly ETL repo (`mtg-db`); this app is read-only and embeds queries only. Two vector spaces are kept apart on purpose — one over card *names*, one over preprocessed oracle *text* — alongside the structured columns (type, mana value, colour identity, keywords, legality) as SQL predicates.

- *Seed card path*: resolve the name by unioning semantic search over the name vectors with lexical fuzzy matching, then **split the card's text into its individual abilities and run one semantic query per ability**, unioning the results. This is the fix for one-card-many-functions.
- *Text path*: a single embedding query, top-50 for recall.

Keeping the two spaces separate matters more than any tuning: `card_text` holds oracle text only, so a name query aimed at it returns cards that merely *mention* the name. Searching for "Lightning Bolt" there never returns Lightning Bolt.

**3. LLM re-ranker.** Candidates are scored against a fixed priority ladder — effect family → scope → speed → mana efficiency → type fit → color identity → legality — with deterministic tie-breaks, deduplication of split/modal/double-faced printings, and removal of zero-overlap candidates. Each surviving card gets a one-sentence factual justification.

The ranker is constrained to the retrieved fields only. **The model supplies reasoning; the index supplies facts.**

## Design decisions

- **Grounding over model size.** Both LLM stages run a small, inexpensive model at low temperature. Retrieved card text does the work a frontier model would only approximate — cheaper *and* more accurate in a niche domain.
- **Deterministic by design.** Single-turn, no agent loop, fixed tie-breaks. The same query returns the same ranking, which is what makes evaluation and iteration possible.
- **Function over popularity.** Ranking reads card text, so an obscure $0.25 card competes with a $65 staple on equal footing.
- **Refusal over guessing.** An out-of-scope query returns a scope message instead of a plausible answer assembled from nothing. A name that resolves too weakly is refused rather than silently matched to the nearest vector — measured separation is wide (genuine misspellings score 81–100 on the fuzzy scale, nonsense 30–60).

## Measured engineering decisions

Two choices were made against numbers rather than defaults. Both are reproducible against a live database with `notebooks/eda.ipynb`.

**Exact search beats the approximate index at this scale.** The database ships a single IVFFlat index spanning all three embedding sources, so a source-filtered query probes one cell and then discards most of it to the filter. At the server's default one probe, recall against an exact baseline fell as low as 0% at k=5. Worse, Postgres only chose the index below roughly `LIMIT 10`, so retrieval quality silently depended on `k`. Brute force over 36k vectors costs ~100–150 ms server-side — negligible beside two LLM calls — so every vector query forces an exact scan and gets deterministic, exactly-correct ranking.

**ONNX runtime instead of torch, verified equivalent.** Streamlit Community Cloud caps apps at 1 GB of memory, which PyTorch alone can exhaust. Swapping to an ONNX build of the same MiniLM weights cut the install from ~1 GB to ~80 MB. Equivalence was measured, not assumed: reconstructing 200 stored vectors gave a minimum cosine similarity of 1.000000, and top-10 retrieval agreed with sentence-transformers 99% of the time — the single disagreement being the last slot of a group of cards at bit-identical distance. `scripts/check_embedding_parity.py` re-checks this after any model change.

## Evaluation

`scripts/eval_judge.py` scores precision with an LLM judge reading each returned card's real fields — of the cards retrieval returns, how many answer the question?

This replaced recall against the 49-query gold set, which turned out to be unmeasurable as labelled: each query names 8 cards where hundreds qualify (185 have flying and vigilance; 640 lands enter untapped), and some labels don't satisfy their own query. Retrieval can return 50 correct cards and score zero. `scripts/eval_retrieval.py` keeps that number as a regression tripwire, where the trend is informative and the absolute value isn't.

The zero-recall queries were the useful output. They cluster into three groups, none of which vector search over oracle text can answer: **slang** ("ramp", "burn", "spellslinger"), **structured predicates** ("2 mana or less", "in rakdos", "Standard-legal"), and **negation** ("lands that enter untapped"). Hand-decomposing them confirms it — "lands that enter untapped" goes from 0% to 38% as a SQL predicate. That is what the roadmap below is for.

## Roadmap

- Planner emits structured filters (colour, mana value, keywords, legality) rather than only a search string — the SQL half of the system is currently unreachable from a user query
- A mechanic taxonomy (keyword and regex patterns per effect family) to expand player slang into oracle phrasing
- Rules and glossary retrieval: 3,674 chunks are indexed and queryable, but the router still declines rules questions
- Price-aware ranking, making budget substitution a first-class objective
