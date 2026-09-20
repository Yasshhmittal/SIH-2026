"""
models/bge.py — BGE-M3 embedding wrapper for NEBULA (Ollama backend).

Responsibilities (from plan §4.3):
  - Encode SOP chunks to dense vectors (once at index time)
  - Encode query at retrieval time
  - Does NOT generate text answers

Uses Ollama embeddings API at localhost:11434.
Model: bge-m3:latest (F16, embedding_length=1024).
"""

from __future__ import annotations

import os
from typing import List

import numpy as np
import ollama

MODEL_NAME = os.getenv("BGE_MODEL", "bge-m3:latest")
# Embeddings are fast; still bound the call so a hung server fails cleanly.
EMBED_TIMEOUT = float(os.getenv("OLLAMA_EMBED_TIMEOUT", "120"))


def _client() -> "ollama.Client":
    """Ollama client with an explicit timeout (fully local, no cloud)."""
    return ollama.Client(timeout=EMBED_TIMEOUT)


class BGE:
    """BGE-M3 embedding model wrapper using Ollama."""

    def unload(self) -> None:
        """Explicitly unload from Ollama to free memory."""
        try:
            _client().generate(model=MODEL_NAME, prompt='', keep_alive=0)
        except Exception:
            pass

    def encode(self, texts: List[str], batch_size: int = 8) -> np.ndarray:
        """
        Encode a list of texts to dense embeddings via Ollama.

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        all_embeddings = []
        client = _client()

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                response = client.embed(
                    model=MODEL_NAME,
                    input=text,
                )
                all_embeddings.append(response["embeddings"][0])

        return np.array(all_embeddings, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a single query string. Returns shape (1, embedding_dim)."""
        return self.encode([query], batch_size=1)
