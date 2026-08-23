"""
Verify that a query-embedding backend is comparable to the vectors in Neon.

Document vectors were written by mtg-db using sentence-transformers. This app
prefers fastembed's ONNX port of the same MiniLM weights because torch does not
fit Streamlit Community Cloud's 1GB memory cap. Same weights is not the same as
same numbers, so measure it rather than assume it.

Two checks:

  1. Reconstruction — re-embed stored chunk_text and compare to the stored
     vector. Isolates backend numerics, since the input text is identical.
  2. Retrieval agreement — run the same probe queries through each backend and
     compare the ranked card lists. This is what actually matters; a small
     numeric drift that never reorders results is harmless.

Usage:
    python -m scripts.check_embedding_parity [--sample 200] [--top-k 10]
"""

import argparse
import json
import sys

import numpy as np

from src.db.neon import query
from src.embeddings import embed_queries

PARITY_THRESHOLD = 0.999

PROBES = [
    "Lightning Bolt",
    "Lightnin Bolt",
    "destroy all creatures",
    "can't be blocked",
    "counter target spell",
    "add one mana of any color",
    "draw a card whenever an opponent casts a spell",
    "create a token copy of a creature",
    "return target creature card from your graveyard to the battlefield",
    "each opponent loses 2 life",
]


def _parse_vector(raw) -> np.ndarray:
    """pgvector arrives as a '[0.1,-0.2,...]' string unless a type adapter is registered."""
    if isinstance(raw, str):
        return np.asarray(json.loads(raw), dtype=np.float64)
    return np.asarray(raw, dtype=np.float64)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def check_reconstruction(backend: str, sample: int) -> dict:
    rows = query(
        """
        SELECT chunk_text, embedding
        FROM embeddings
        WHERE source = 'card_text' AND length(chunk_text) > 0
        ORDER BY md5(id)
        LIMIT %(sample)s
        """,
        {"sample": sample},
    )
    stored = [_parse_vector(row["embedding"]) for row in rows]
    fresh = embed_queries([row["chunk_text"] for row in rows], backend=backend)
    sims = np.array(
        [_cosine(s, np.asarray(f, dtype=np.float64)) for s, f in zip(stored, fresh)]
    )
    return {
        "n": len(sims),
        "min": sims.min(),
        "mean": sims.mean(),
        "p01": np.percentile(sims, 1),
        "below_threshold": int((sims < PARITY_THRESHOLD).sum()),
    }


def _top_k_names(vector: list[float], k: int) -> list[str]:
    rows = query(
        """
        SELECT c.name
        FROM embeddings e
        JOIN cards c
          ON c.scryfall_oracle_id = split_part(e.id, ':', 1)
         AND c.face_index = split_part(e.id, ':', 2)::int
        WHERE e.source = 'card_text'
          AND length(e.chunk_text) > 0
        ORDER BY e.embedding <=> %(qvec)s::vector
        LIMIT %(k)s
        """,
        {"qvec": json.dumps(vector), "k": k},
    )
    return [row["name"] for row in rows]


def check_retrieval_agreement(backends: list[str], top_k: int) -> list[dict]:
    results = []
    for probe in PROBES:
        ranked = {b: _top_k_names(embed_queries([probe], backend=b)[0], top_k) for b in backends}
        first, second = (ranked[b] for b in backends)
        results.append(
            {
                "probe": probe,
                "overlap": len(set(first) & set(second)) / top_k,
                "identical_order": first == second,
                "top1_match": bool(first and second and first[0] == second[0]),
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--backends", nargs="+", default=["fastembed", "huggingface"])
    args = parser.parse_args()

    print(f"Reconstruction vs stored vectors (n={args.sample})")
    recon = {}
    for backend in args.backends:
        stats = check_reconstruction(backend, args.sample)
        recon[backend] = stats
        print(
            f"  {backend:<14} min={stats['min']:.6f}  p01={stats['p01']:.6f}  "
            f"mean={stats['mean']:.6f}  below {PARITY_THRESHOLD}: "
            f"{stats['below_threshold']}/{stats['n']}"
        )

    if len(args.backends) < 2:
        return 0

    print(f"\nRetrieval agreement between {args.backends[0]} and {args.backends[1]} (top-{args.top_k})")
    agreement = check_retrieval_agreement(args.backends[:2], args.top_k)
    for row in agreement:
        flag = "" if row["identical_order"] else ("  ~order" if row["overlap"] == 1.0 else "  DIFFERS")
        print(f"  {row['overlap']:>5.0%}  {row['probe'][:58]:<58}{flag}")

    mean_overlap = sum(r["overlap"] for r in agreement) / len(agreement)
    top1 = sum(r["top1_match"] for r in agreement) / len(agreement)
    print(f"\n  mean overlap {mean_overlap:.1%} | top-1 match {top1:.0%}")

    primary = recon[args.backends[0]]
    if primary["min"] < PARITY_THRESHOLD:
        print(
            f"\nFAIL: {args.backends[0]} min cosine {primary['min']:.6f} "
            f"< {PARITY_THRESHOLD}. Prefer EMBEDDING_BACKEND=huggingface."
        )
        return 1
    print(f"\nPASS: {args.backends[0]} is comparable to the stored vectors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
