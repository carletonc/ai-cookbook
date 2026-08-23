# AI MTG Card Search

Find Magic: The Gathering cards by **function** — alternatives to a named card, or cards that match a described effect — then rank them with a short factual rationale.

## About

A general-purpose LLM does not know Magic's rules; it approximates them from a thin slice of training data. Plain semantic search fails too: *destroy*, *exile*, and *sacrifice* sit next to each other in embedding space, player slang (*ramp*, *board wipe*) never appears on the card, and one card can be three functions at once.

This app routes the query, retrieves from a card database, and asks a small model only to rank what was retrieved. The model supplies reasoning; the index supplies facts. Out-of-scope asks (rules adjudication, "what commander should I build") are refused rather than guessed.

Card data lives in Neon Postgres with `pgvector`, maintained weekly by a separate ETL (`mtg-db`). This app is **read-only** and embeds queries only — name search and text search use two different vector spaces on purpose.

The longer design write-up (problem, architecture, measured decisions, roadmap) is [`src/ui/ABOUT.md`](src/ui/ABOUT.md). The Streamlit expander loads that file.

## Setup

Copy `.env.example` to `.env` and set:

| Variable | Required for | Notes |
|---|---|---|
| `DATABASE_URL` | Every search | Neon connection string. Use a **read-only** role (`SELECT` on `cards`, `embeddings`, `sync_log`). The Streamlit Cloud app needs the same value in secrets before merging to `main`. |
| `OPENAI_API_KEY` | Planner + ranker | The Streamlit sidebar asks for this at runtime so a visitor's key is never stored. Put it in `.env` as well for notebooks and `scripts/eval_judge.py`. |

Leave `EMBEDDING_BACKEND=fastembed` unless you are debugging parity against `sentence-transformers`. That model must stay MiniLM, 384-dim, cosine — the same weights `mtg-db` wrote into Neon.

```bash
cd apps/ai_mtg_search
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit DATABASE_URL (and OPENAI_API_KEY for scripts)
streamlit run app.py          # paste an OpenAI key in the sidebar, then search
```

Try `cards like Chatterfang` or `draw a card whenever an opponent casts a spell`.

## Layout

```
app.py                 Streamlit entry
src/                   Product code (retrieval, LLM, UI)
src/ui/ABOUT.md        In-app about copy
notebooks/             EDA and eval runners
scripts/               CLI: embedding parity, recall, judge
data/                  Eval gold set; unused slang taxonomy
```

## Evaluation

- `notebooks/eda.ipynb` — why vector queries force exact scans, and why ONNX embeddings match the stored vectors
- `python -m scripts.eval_judge` — precision of returned cards (`OPENAI_API_KEY` in `.env`)
- `python -m scripts.eval_retrieval` — recall against `data/gold.json` (a tripwire; the labels are too thin to score retrieval well)
