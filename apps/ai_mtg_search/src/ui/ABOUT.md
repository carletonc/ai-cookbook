## Motivation

An LLM answers from the average of its training data, and Magic is a small slice of that corpus, so a general-purpose model doesn't know the game's rules — it approximates them, fluently and wrongly. A bigger model doesn't change the mixture, and a model that self-corrects is correcting against the same thin prior without properly engineered context.

Four properties of the domain also break plain semantic search:

1. **Technical vocabulary.** Ordinary words are load-bearing rules terms: to *mill* is to move cards from library to graveyard, and *counter* means both cancelling a spell and a marker sitting on a creature. The collisions have mechanical consequences — *destroy*, *exile*, and *sacrifice* all read as "removal," but indestructible stops only the first, exile doesn't count as dying (so death triggers never fire), and sacrifice ignores both. Embeddings put these terms next to each other because English does; the rules pull them apart.
2. **Embedded slang.** *Mana rock*, *board wipe*, and *impulse draw* appear nowhere in official card text or the rulebook, yet they're how players actually search. *Tutor* is the same kind of word: a few titles use it (*Demonic Tutor*), but the printed effect is "search your library," and most cards that do that do not say tutor at all. A name-vector hit on "tutor" therefore misses the effect, and a text-vector hit on "tutor" misses the name. Some slang also inverts the plain meaning: impulse draw isn't drawing at all — it exiles cards to play temporarily, so none of the "whenever you draw" triggers a model would assume actually fire.
3. **One need, many mechanics.** "Stop a flying creature" is served by several unrelated functions — reach, removal, ability-stripping, or a global effect — each with entirely different card text.
4. **One card, many functions.** A single card can be ramp, lifegain, and card draw at once. Embedding it as one document blurs all three into one vector.

What makes that worth solving is the shape of the game itself. The strongest cards are often prohibitively expensive, and the well-known answers are the ones everyone already plays — so players are optimizing for two things at once: spend less, and don't play the same deck as the table next to them. Somewhere in a 33,000+ card legal pool there is usually a cheaper, less-played card that does the job. Finding it is a retrieval and ranking problem that no tool does well (yet).

## Architecture

```
Query → Router (LLM) → Name resolve or text search → [picker if needed] → Re-ranker (LLM) → Write-up
```

**1. Router.** An LLM classifies the query into `seed_card` ("alternatives to Rhystic Study"), `text_search` ("draw when opponents cast spells"), or `unsupported`, returning strict JSON. Intent chooses the path; empty or weak hits do not switch routes. Out-of-scope asks — rules adjudication, price-only, "what commander should I build" — are declined rather than answered badly. The cheapest fix for a hallucination is not answering.

**2. Retrieval.** Card data lives in Neon Postgres with `pgvector`, maintained by a separate weekly ETL repo (`mtg-db`); this app is read-only (prefer a reader role) and embeds queries only. Two vector spaces are kept apart on purpose — one over card *names*, one over preprocessed oracle *text* — alongside the structured columns (type, mana value, colour identity, keywords, legality) as SQL predicates. Those filters are implemented; the router does not emit them yet.

- *Seed card path*: resolve the name with exact title, then SQL contains (character lines like Narset), then a union of name-vector neighbours and RapidFuzz with a floor and a gap from the best score. Several hits, or a weak unique typo, open a picker; only a high-confidence unique typo continues on its own. After a seed is chosen, **split its oracle text into abilities and run one text search per ability**, keep the higher similarity per card, and drop the seed. That is the fix for one-card-many-functions.
- *Text path*: one embedding query, one string, top-50, with a 0.6 cosine floor. Name matching is not mixed in.

Keeping the two spaces separate matters more than any tuning: `card_text` holds oracle text only, so a name query aimed at it returns cards that merely *mention* the name. Searching for "Lightning Bolt" there never returns Lightning Bolt.

**3. LLM re-ranker.** Candidates are scored against a fixed priority ladder — effect family → scope → speed → mana efficiency → type fit → color identity → legality. Mana efficiency uses the numeric mana value (lower is usually better, then extra or conditional costs in the text); the write-up cites the printed mana cost, not "mv". Split, modal, and double-faced printings are collapsed; cards with no functional overlap are dropped. Each surviving card gets a short factual justification.

The ranker is constrained to the retrieved fields only. **The model supplies reasoning; the index supplies facts.** After a seed search, the UI keeps that card's art and text on the page so the write-up has something to compare against.

## Design decisions

- **Grounding over model size.** Both LLM stages run a small, inexpensive model at low temperature. Retrieved card text does the work a frontier model would only approximate — cheaper *and* more accurate in a niche domain.
- **Deterministic retrieval, not a deterministic write-up.** Single-turn, no agent loop. Vector search is an exact scan with a stable secondary sort; name resolution is a fixed ladder. The ranker follows a fixed priority list at temperature 0.1, but it has no seed — the same query can change wording and the last few ranks.
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

- Planner emits structured filters (colour, mana value, keywords, legality) rather than only a search string — `_build_filters` already matches the Neon `cards` columns; the router still does not fill it
- Player slang still fails as a `card_text` query ("ramp", "burn", "spellslinger"). Expanding those phrases into oracle wording is future work; it is not on the live search path
- Rules and glossary retrieval: 3,674 chunks are indexed and queryable, but the router still declines rules questions
- Price-aware ranking, making budget substitution a first-class objective
