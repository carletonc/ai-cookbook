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
| `DATABASE_URL_READONLY` | Every search | Prefer this. Neon **read-only** role (`SELECT` on `cards`, `embeddings`, `sync_log`). Falls back to `DATABASE_URL` if unset. Put the reader URL in Streamlit secrets before merging to `main`. |
| `GROQ_API_KEY` (or `LLM_API_KEY`) | Planner + ranker + judge | App-held key — visitors do **not** paste one. Default host is Groq (`LLM_BASE_URL` / `LLM_MODEL=openai/gpt-oss-20b`). HF, OpenAI, and xAI work by changing `LLM_BASE_URL` + model + the matching key alias. |
| `LLM_DAILY_REQUEST_CAP` | Optional | Soft **per-process** demo cap (default `800`; `0` disables). Resets on restart; provider rate limits are the real backstop. |

Leave `EMBEDDING_BACKEND=fastembed` unless you are debugging parity against `sentence-transformers`. That model must stay MiniLM, 384-dim, cosine — the same weights `mtg-db` wrote into Neon.

```bash
cd apps/ai_mtg_search
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # DATABASE_URL_READONLY + GROQ_API_KEY
streamlit run app.py
```

Use the **Try these** buttons in the UI, or type e.g. `cards like Chatterfang` / `draw a card whenever an opponent casts a spell`.

## Layout

```
app.py                 Streamlit entry
src/                   Product code (retrieval, LLM, UI)
src/ui/ABOUT.md        In-app about copy
notebooks/             EDA and eval runners
scripts/               CLI: embedding parity, recall, judge
data/                  Eval gold set
```

## Evaluation

- `notebooks/eda.ipynb` — why vector queries force exact scans, and why ONNX embeddings match the stored vectors
- `python -m scripts.eval_judge` — precision of returned cards via the same OpenAI-compatible host as the app (default Groq `openai/gpt-oss-20b`)
- `python -m scripts.eval_retrieval` — recall against `data/gold.json` (a tripwire; the labels are too thin to score retrieval well)
