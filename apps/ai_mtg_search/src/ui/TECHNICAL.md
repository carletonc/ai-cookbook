These are choices about *how* the system is built. About is the product problem. This is the stack.

## MiniLM embeds; a small chat model ranks

**Embeddings: `sentence-transformers/all-MiniLM-L6-v2`, 384-d, cosine.** BERT WordPiece (~30k pieces, not one token per word). Unseen English-like words still embed (`Squirrelfolk` → `squirrel` + `##folk`). Game notation *does* tokenize — badly. `{T}` becomes `{`, `t`, `}`, which has nothing to do with *tap*, so raw symbols retrieve poorly. 384-d makes an exact scan of ~36k vectors ~100–150 ms, so we can skip the approximate IVFFlat index. Cosine (`<=>`) is scale-invariant — fastembed (normalized) and sentence-transformers (not) share the same stored vectors.

**Chat: Groq `openai/gpt-oss-20b` (host is swappable).** Small on purpose. A larger model would still guess Magic from a thin prior. The index holds facts; this model only routes the query and ranks retrieved rows. Temperature 0.1, no seed — write-ups are not bit-identical. `reasoning_effort=low` and a 2048-token ranker cap keep hidden reasoning from blowing Groq's free-tier TPM.

## MiniLM vs TF-IDF embeddings

The corpus is small and the documents are short. In early experiments, TF-IDF / BM25 over oracle text was a strong, cheap baseline — the kind of lexical retrieval that works well in a traditional RecSys pipeline when the query already uses printed words ("draw two cards").

This pipeline has to accept a wider mix of inputs: a card name, a paraphrase of an effect, a typo, a character line, slang that never appears on the card. That is a set of retrieval *functions*, not one keyword match, so we use a denser model. MiniLM is weak on slang ("ramp") and strong on paraphrase ("make squirrel tokens" ≈ "create a 1/1 green Squirrel creature token"). Later we can add embedding spaces chosen by intent (name vs text vs the next transform) and route the query to the right one. A BM25 + MiniLM hybrid is still an honest experiment. It is not what is running.

## Notation tokenizes; it just retrieves poorly

Raw `{T}` and `{W/P}` are valid WordPiece — braces, letters, slashes. Those pieces do not mean *tap* or *Phyrexian* or *two life*, so the vector sits in the wrong neighborhood. `{E}{E}{E}` is a punctuation blob. A card that names itself in its rules ("Lightning Bolt deals 3 damage") pulls the vector toward the title, not the effect.

`mtg-db` embeds **preprocessed** oracle text. This app runs the same vendored function on queries that contain `{`. If the copies drift, recall dies with no error.

- Dual-expand every `{symbol}`: `{W/P}` → `Phyrexian white mana (white mana or 2 life)` so jargon and functional queries both hit.
- Replace the card's own name with `this card`.
- Keep reminder text (~31% of cards).
- Normalize a small set of non-ASCII game characters.

On MiniLM, cosine for "Phyrexian mana" went 0.14 → 0.63, "hybrid mana cost" 0.01 → 0.59, "tap to add green" 0.24 → 0.95 (dual; functional-only is slightly higher on that last one). Queries without braces are not rewritten. `card_text` holds only that cleaned oracle text — names and costs stay on SQL columns — so a name query against it never returns the named card.

## V1 was Pinecone; this version is Postgres + pgvector

**v1** stored each vector and its metadata on one Pinecone row. That was already "all in one place." Embedding a source there does **not** keep the raw text as something you can `SELECT`. To show oracle text, re-transform it, or debug a hit, you had to stuff a copy into metadata or call a second store.

**This version** stores the catalog **once**. `cards` is the source of truth; `embeddings` rows join to it. Pinecone copies metadata onto every vector, so a second transform duplicates the card. Here a new `source` (`card_name`, `card_text`, `rules`, …) is another vector pointed at the same row — smaller, and you can reshape the text without cloning the catalog. Type, colour identity, keywords, mana value, and legality are real columns. The original string stays in Postgres next to the vector. Filter, then vector (Dimir, commander-legal, mana value ≤ 3, then cosine). More efficient, more flexible.

This app embeds queries only. `mtg-db` owns writes and new embedding spaces.

The shared IVFFlat index spans every `source`, so a source filter wrecks approximate recall and Postgres only used the index below roughly `LIMIT 10`. We force an exact scan (`notebooks/eda.ipynb`). The index is an implementation detail. The schema is the design.

## fastembed / ONNX so the host fits in 1 GB

**fastembed** loads MiniLM through ONNX Runtime (~80 MB) instead of PyTorch (~1 GB), which would exhaust Streamlit Community Cloud's 1 GB cap. Parity against sentence-transformers: minimum cosine 1.000000 on 200 reconstructed vectors; top-10 agreed 99% (the miss was the last slot of a bit-identical-distance group). `scripts/check_embedding_parity.py` re-checks after a backend change. The torch path stays as an escape hatch. Document vectors are never rebuilt here.
