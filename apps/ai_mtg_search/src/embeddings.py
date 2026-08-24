"""
Query embedding.

This app embeds **queries only** — document vectors are written weekly by
the `mtg-db` ETL repo and are never regenerated here.

Two backends produce comparable vectors from the same MiniLM weights:

  fastembed     ONNX runtime, ~80MB installed. Streamlit Community Cloud
                caps apps at 1GB RAM, which torch alone can exhaust.
  huggingface   sentence-transformers + torch, identical to what mtg-db
                ran. Heavier; kept as an escape hatch.

fastembed L2-normalizes its output and sentence-transformers does not.
That difference is invisible here because ranking uses pgvector's cosine
operator (`<=>`), which is scale-invariant. It would matter under `<#>`
(inner product) or `<->` (L2).

Verify any backend change with scripts/check_embedding_parity.py.
"""

from src.config import EMBED_DIM, EMBED_MODEL, EMBEDDING_BACKEND

_backend = None
_encode = None


def _load_fastembed():
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=EMBED_MODEL)

    def encode(texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in model.embed(texts)]

    return encode


def _load_sentence_transformers():
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBED_MODEL)

    def encode(texts: list[str]) -> list[list[float]]:
        vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return [vector.tolist() for vector in vectors]

    return encode


_LOADERS = {
    "fastembed": _load_fastembed,
    "huggingface": _load_sentence_transformers,
}


def _get_encoder(backend: str | None = None):
    """Load the encoder once per process. Heavy imports stay inside the loaders."""
    global _backend, _encode
    backend = backend or EMBEDDING_BACKEND
    if _encode is None or _backend != backend:
        try:
            loader = _LOADERS[backend]
        except KeyError:
            raise ValueError(
                f"Unknown EMBEDDING_BACKEND {backend!r}; "
                f"expected one of {sorted(_LOADERS)}."
            ) from None
        _encode = loader()
        _backend = backend
    return _encode


def embed_queries(texts: list[str], *, backend: str | None = None) -> list[list[float]]:
    """Embed a batch of query strings."""
    if not texts:
        return []
    vectors = _get_encoder(backend)(texts)
    if vectors and len(vectors[0]) != EMBED_DIM:
        raise ValueError(
            f"{_backend} produced {len(vectors[0])}-dim vectors but the "
            f"embeddings table holds {EMBED_DIM}-dim. These are not comparable."
        )
    return vectors


def embed_query(text: str, *, backend: str | None = None) -> list[float]:
    """Embed a single query string."""
    return embed_queries([text], backend=backend)[0]
