"""
Retrieval recall against the labelled gold set.

Measures the retrieval stage in isolation — no planner, no ranker. The gold
queries are full natural-language questions ("What cards that make the most
squirrel tokens?"), whereas at runtime the planner compresses them to a search
phrase ("make squirrel tokens"). So these numbers are a floor, not the
pipeline's score.

Cards the ranker never sees cannot be ranked, which makes recall the metric
that matters here. Unresolvable expected names are reported separately: a gold
entry naming a card that is not in `cards` is a stale label, not a miss.

Usage:
    python -m scripts.eval_retrieval [--k 50] [--limit N] [--verbose]
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

from src.db.neon import query
from src.search import search_card_text

GOLD_PATH = Path(__file__).resolve().parent.parent / "gold.json"


def _normalize(name: str) -> str:
    return " ".join(name.lower().replace("’", "'").split())


def _variants(name: str) -> set[str]:
    """Gold labels and stored names disagree on subtitles and split faces."""
    base = _normalize(name)
    forms = {base}
    for separator in (" // ", ","):
        if separator in base:
            forms.add(base.split(separator)[0].strip())
    return forms


def resolve_expected(names: set[str]) -> dict[str, bool]:
    """Check which expected card names exist in the corpus at all."""
    rows = query(
        "SELECT DISTINCT name FROM cards WHERE lower(name) = ANY(%(names)s)",
        {"names": [_normalize(n) for n in names]},
    )
    found = {_normalize(row["name"]) for row in rows}
    # Fall back to prefix matching for subtitled cards ("Chatterfang" vs
    # "Chatterfang, Squirrel General").
    missing = {n for n in names if _normalize(n) not in found}
    if missing:
        prefix_rows = query(
            """
            SELECT DISTINCT name FROM cards
            WHERE lower(name) LIKE ANY(%(patterns)s)
            """,
            {"patterns": [f"{_normalize(n)}%" for n in missing]},
        )
        prefixes = [_normalize(r["name"]) for r in prefix_rows]
        for name in list(missing):
            if any(p.startswith(_normalize(name)) for p in prefixes):
                missing.discard(name)
    return {n: n not in missing for n in names}


def evaluate(k: int, limit: int | None, verbose: bool) -> int:
    gold = json.loads(GOLD_PATH.read_text())
    if limit:
        gold = gold[:limit]

    all_expected = {name for case in gold for name in case["expected_cards"]}
    in_corpus = resolve_expected(all_expected)
    absent = sorted(n for n, present in in_corpus.items() if not present)

    per_case = []
    for case in gold:
        retrieved = search_card_text(case["query"], k=k)
        retrieved_forms = set()
        for row in retrieved:
            retrieved_forms |= _variants(row["name"])

        expected = [n for n in case["expected_cards"] if in_corpus[n]]
        hits = [n for n in expected if _variants(n) & retrieved_forms]
        recall = len(hits) / len(expected) if expected else float("nan")
        per_case.append(
            {
                "query": case["query"],
                "sub_intent": case.get("sub_intent"),
                "recall": recall,
                "hit": bool(hits),
                "n_expected": len(expected),
            }
        )
        if verbose:
            print(f"  {recall:>5.0%}  {case['query'][:64]}")
            missed = [n for n in expected if n not in hits]
            if missed:
                print(f"         missed: {', '.join(missed[:6])}")

    recalls = [c["recall"] for c in per_case if c["n_expected"]]
    print(f"\nRetrieval recall@{k} over {len(per_case)} gold queries")
    print(f"  mean recall  {statistics.mean(recalls):.1%}")
    print(f"  median       {statistics.median(recalls):.1%}")
    print(f"  hit rate     {sum(c['hit'] for c in per_case) / len(per_case):.1%}")
    print(f"  zero-recall  {sum(1 for r in recalls if r == 0)}/{len(recalls)} queries")

    by_intent: dict[str, list[float]] = {}
    for case in per_case:
        if case["n_expected"]:
            by_intent.setdefault(case["sub_intent"] or "unlabelled", []).append(case["recall"])
    if len(by_intent) > 1:
        print("\n  by sub_intent")
        for intent, values in sorted(by_intent.items()):
            print(f"    {intent:<16} {statistics.mean(values):>6.1%}  (n={len(values)})")

    if absent:
        print(f"\n  {len(absent)}/{len(all_expected)} expected cards are not in the corpus")
        print("  (stale gold labels, excluded from recall):")
        for name in absent[:15]:
            print(f"    - {name}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=50)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    return evaluate(args.k, args.limit, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
