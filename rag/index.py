"""
rag/index.py — Offline BGE-M3 embedding cache builder.

Strategy (from plan §5.3):
  - Compute embeddings once → save to cache/embeddings.npy + cache/chunks.json
  - Reload cache on subsequent runs (no re-embedding needed)
  - Cache is keyed by SOP filename to detect stale caches
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import List, Tuple

import numpy as np

from core.schemas import Chunk

CACHE_DIR = Path(os.getenv("CACHE_DIR", "./cache"))


def _cache_key(sop_path: str) -> str:
    """Hash the SOP file to detect when re-indexing is needed."""
    path = Path(sop_path)
    if not path.exists():
        return ""
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def _cache_paths(sop_path: str) -> Tuple[Path, Path, Path]:
    """Return (embeddings_path, chunks_path, meta_path)."""
    key = _cache_key(sop_path)
    stem = Path(sop_path).stem
    base = CACHE_DIR / f"{stem}_{key}"
    return base.with_suffix(".npy"), base.with_name(base.stem + "_chunks.json"), base.with_name(base.stem + "_meta.json")


def _save_index(embeddings: np.ndarray, chunks: List[Chunk], sop_path: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    emb_path, chunks_path, meta_path = _cache_paths(sop_path)

    np.save(str(emb_path), embeddings)
    with open(chunks_path, "w") as f:
        json.dump([c.__dict__ for c in chunks], f, indent=2)
    with open(meta_path, "w") as f:
        json.dump({"sop_path": sop_path, "chunk_count": len(chunks)}, f)
    print(f"[Index] Saved: {emb_path.name} ({len(chunks)} chunks)")


def _load_index(sop_path: str) -> Tuple[np.ndarray, List[Chunk]] | None:
    """Return cached (embeddings, chunks) or None if cache is missing/stale."""
    emb_path, chunks_path, _ = _cache_paths(sop_path)
    if not emb_path.exists() or not chunks_path.exists():
        return None

    embeddings = np.load(str(emb_path))
    with open(chunks_path) as f:
        raw = json.load(f)

    chunks = [Chunk(**item) for item in raw]
    print(f"[Index] Loaded cache: {emb_path.name} ({len(chunks)} chunks)")
    return embeddings, chunks


def build_or_load_index(
    chunks: List[Chunk],
    sop_path: str,
) -> Tuple[np.ndarray, List[Chunk]]:
    """
    Load existing embedding cache or compute and save a new one.

    Args:
        chunks:     Pre-chunked SOP document.
        sop_path:   Original SOP PDF path (used for cache key).

    Returns:
        (embedding_matrix [N, D], chunk_list [N])
    """
    cached = _load_index(sop_path)
    if cached is not None:
        return cached

    # Cache miss — compute embeddings
    print(f"[Index] Computing embeddings for {len(chunks)} chunks...")
    from models.bge import BGE
    bge = BGE()
    texts = [c.text for c in chunks]
    embeddings = bge.encode(texts)
    bge.unload()

    _save_index(embeddings, chunks, sop_path)
    return embeddings, chunks
