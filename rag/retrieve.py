"""
rag/retrieve.py — Cosine top-k retrieval using NumPy (no vector DB).

Strategy (from plan §2.3 + §5.4):
  SOP embeddings.npy → cosine similarity → top-3 chunks
  Query = user task + extracted findings
  No Qdrant, no Elasticsearch, no reranker.
"""

from __future__ import annotations

from typing import List

import numpy as np

from core.schemas import Chunk, RetrievedChunk
from models.bge import BGE


def cosine_similarity_matrix(query_vec: np.ndarray, doc_matrix: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between one query vector and all doc vectors.

    Args:
        query_vec:   shape (D,) or (1, D)
        doc_matrix:  shape (N, D)

    Returns:
        scores: shape (N,)
    """
    q = query_vec.flatten()
    q_norm = q / (np.linalg.norm(q) + 1e-10)

    norms = np.linalg.norm(doc_matrix, axis=1, keepdims=True) + 1e-10
    doc_normed = doc_matrix / norms

    return doc_normed @ q_norm   # shape (N,)


def retrieve_top_k(
    query: str,
    embedding_matrix: np.ndarray,
    chunks: List[Chunk],
    bge: BGE,
    k: int = 3,
) -> List[RetrievedChunk]:
    """
    Encode query with BGE-M3 and return top-k most similar SOP chunks.

    Args:
        query:            Combined query string (task + findings).
        embedding_matrix: Precomputed doc embeddings, shape (N, D).
        chunks:           Corresponding Chunk list of length N.
        bge:              Loaded BGE instance.
        k:                Number of top chunks to return.

    Returns:
        List of RetrievedChunk sorted by descending similarity score.
    """
    query_vec = bge.encode_query(query)   # shape (1, D)
    scores = cosine_similarity_matrix(query_vec, embedding_matrix)   # (N,)

    # Get top-k indices (highest scores)
    top_indices = np.argsort(scores)[::-1][:k]

    return [
        RetrievedChunk(chunk=chunks[i], score=float(scores[i]))
        for i in top_indices
    ]
