"""Local embeddings via Ollama, pinned to CPU.

bge-m3 runs on CPU by design: on the 6 GB target GPU it would occupy 1.2 GB
that a generative model needs, and embedding is short and batchable. Ingest is
offline work and a query embedding is one short string, so CPU latency is not
on the critical path.

If the embedding model is unavailable the caller still gets results — retrieval
degrades to BM25 alone rather than failing. Keyword search over the org's own
documents is a reasonable floor; no search at all is not.
"""

from __future__ import annotations

import logging

import httpx
import numpy as np

log = logging.getLogger("prahari.knowledge.embed")

EMBED_MODEL = "bge-m3"
EMBED_DIM = 1024
_OLLAMA = "http://127.0.0.1:11434"

# Ollama loads the model on the first call; later calls are much faster.
_TIMEOUT = httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0)


class EmbeddingUnavailable(RuntimeError):
    pass


def embed_texts(texts: list[str], model: str = EMBED_MODEL) -> list[np.ndarray]:
    """Embed a batch. Raises EmbeddingUnavailable if the model cannot be used."""
    if not texts:
        return []

    try:
        with httpx.Client(base_url=_OLLAMA, timeout=_TIMEOUT) as client:
            response = client.post("/api/embed", json={"model": model, "input": texts})
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise EmbeddingUnavailable(
            f"{model} returned HTTP {exc.response.status_code}. "
            f"Is it pulled?  ollama pull {model}"
        ) from exc
    except httpx.HTTPError as exc:
        raise EmbeddingUnavailable(f"cannot reach Ollama: {exc}") from exc

    vectors = payload.get("embeddings") or []
    if len(vectors) != len(texts):
        raise EmbeddingUnavailable(
            f"expected {len(texts)} embeddings, got {len(vectors)}"
        )
    return [np.asarray(v, dtype=np.float32) for v in vectors]


def embed_query(text: str, model: str = EMBED_MODEL) -> np.ndarray | None:
    """Embed one query, or None if embeddings are unavailable.

    Returns None rather than raising: a query should still run on BM25 alone.
    """
    try:
        vectors = embed_texts([text], model=model)
        return vectors[0] if vectors else None
    except EmbeddingUnavailable as exc:
        log.warning("query embedding unavailable, falling back to BM25: %s", exc)
        return None


def embed_chunks(
    texts: list[str], model: str = EMBED_MODEL, batch_size: int = 16
) -> tuple[list[np.ndarray], str | None]:
    """Embed chunks in batches.

    Returns (vectors, error). On failure the vectors list is empty and the
    error is returned for surfacing in the UI — the document is still indexed
    for keyword search.
    """
    collected: list[np.ndarray] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        try:
            collected.extend(embed_texts(batch, model=model))
        except EmbeddingUnavailable as exc:
            return [], str(exc)
    return collected, None
