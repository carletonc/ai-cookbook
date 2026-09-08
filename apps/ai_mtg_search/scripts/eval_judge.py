"""
Judge-scored retrieval precision against the gold queries.

`scripts/eval_retrieval.py` measures recall against `data/gold.json`'s
`expected_cards`, which is unreliable: the labels name 8 cards where hundreds
qualify (185 have flying and vigilance; 640 lands enter untapped), and some do
not satisfy their own query. So recall there reads as ~10% even when every
returned card is a good answer.

This script measures the complementary quantity, which the labels *can* support:
of the cards retrieval actually returns, how many satisfy the query? An LLM
judge reads each candidate's real fields and rules on it, so precision scales
past 8 positives without relabelling anything.

The judge uses the same OpenAI-compatible settings as the app (`LLM_BASE_URL`,
`LLM_MODEL`, `GROQ_API_KEY` / aliases) so free-tier Groq works without an
OpenAI key.

Judgements are cached in .eval_cache/judge.json, keyed by query, card and model,
so reruns after a retrieval change only pay for candidates not seen before.

Results are split by gold `path` / `coverage` / `gap`. Precision on
`current` text_search is the number that can move; aspirational gaps are
expected to stay low until that work ships.

Usage:
    python -m scripts.eval_judge [--k 20] [--limit N] [--model openai/gpt-oss-20b]
"""

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

from openai import OpenAI

from src.config import LLM_BASE_URL, LLM_MODEL, get_llm_api_key
from src.search import search_card_text
from scripts.eval_retrieval import gold_labels, load_gold, print_label_breakdowns

APP_DIR = Path(__file__).resolve().parent.parent
GOLD_PATH = APP_DIR / "data" / "gold.json"
CACHE_PATH = APP_DIR / ".eval_cache" / "judge.json"

JUDGE_SYSTEM = (
    "You judge whether Magic: The Gathering cards satisfy a player's search "
    "request. Rule only on the card fields given; never rely on memory of the "
    "card. A card qualifies if it plausibly answers the request, even if it is "
    "not among the best answers. Reject cards that merely mention related "
    "words without having the requested function."
)

JUDGE_INSTRUCTION = """Request: {query}

Candidates:
{candidates}

For each numbered candidate, decide whether it satisfies the request.
Reply with JSON only: {{"verdicts": [{{"n": <number>, "ok": <true|false>}}, ...]}}
Include every candidate exactly once."""


def _card_line(index: int, card: dict) -> str:
    parts = [
        f"{index}. {card['name']}",
        card.get("type_line") or "",
        card.get("mana_cost") or "",
    ]
    if card.get("color_identity"):
        parts.append("/".join(card["color_identity"]))
    text = (card.get("oracle_text") or "").replace("\n", " ")
    parts.append(text[:220] or "(no oracle text)")
    return " | ".join(p for p in parts if p)


def _cache_key(query: str, card_name: str, model: str) -> str:
    raw = f"{model}\x00{query}\x00{card_name}"
    return hashlib.md5(raw.encode()).hexdigest()


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=0))


def judge(client, model: str, query: str, cards: list[dict], cache: dict) -> list[bool]:
    """Return one verdict per card, consulting and filling the cache."""
    pending = [
        (i, card)
        for i, card in enumerate(cards)
        if _cache_key(query, card["name"], model) not in cache
    ]

    if pending:
        listing = "\n".join(_card_line(n, card) for n, (_, card) in enumerate(pending, 1))
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": JUDGE_INSTRUCTION.format(query=query, candidates=listing)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        verdicts = json.loads(content).get("verdicts", [])
        by_number = {v["n"]: bool(v.get("ok")) for v in verdicts if "n" in v}
        for n, (_, card) in enumerate(pending, 1):
            cache[_cache_key(query, card["name"], model)] = by_number.get(n, False)

    return [cache[_cache_key(query, card["name"], model)] for card in cards]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=20)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--model",
        default=LLM_MODEL,
        help=f"Chat model id (default: {LLM_MODEL} from env / Groq demo default)",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    api_key = get_llm_api_key()
    if not api_key:
        print(
            "No LLM API key set. Add GROQ_API_KEY (or LLM_API_KEY) to .env "
            "to run the judge."
        )
        return 2

    client = OpenAI(api_key=api_key, base_url=LLM_BASE_URL)
    cache = _load_cache()
    gold = load_gold(args.limit)

    print(f"Judge host: {LLM_BASE_URL}  model: {args.model}")

    rows = []
    try:
        for case in gold:
            query = case["query"]
            cards = search_card_text(query, k=args.k)
            verdicts = judge(client, args.model, query, cards, cache)
            precision = sum(verdicts) / len(verdicts) if verdicts else 0.0
            labels = gold_labels(case)
            rows.append(
                {
                    "query": query,
                    "precision": precision,
                    "n": len(verdicts),
                    **labels,
                }
            )
            if args.verbose:
                print(f"  {precision:>5.0%}  {labels['coverage']:<13}  {query[:50]}")
                rejected = [c["name"] for c, ok in zip(cards, verdicts) if not ok]
                if rejected:
                    print(f"         rejected: {', '.join(rejected[:5])}")
    finally:
        _save_cache(cache)

    precisions = [r["precision"] for r in rows]
    print(f"\nJudge-scored precision@{args.k} over {len(rows)} queries ({args.model})")
    print(f"  mean precision   {statistics.mean(precisions):.1%}")
    print(f"  median           {statistics.median(precisions):.1%}")
    print(f"  queries at 0%    {sum(1 for p in precisions if p == 0)}/{len(precisions)}")
    print_label_breakdowns(rows, "precision")

    worst = sorted(rows, key=lambda r: r["precision"])[:8]
    print("\n  weakest queries")
    for row in worst:
        print(f"    {row['precision']:>5.0%}  {row['query'][:64]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
