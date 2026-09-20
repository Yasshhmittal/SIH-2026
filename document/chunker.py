"""
document/chunker.py — Evidence chunk creation for NEBULA RAG pipeline.

Chunking strategy (from plan §5.2):
  - ~300–600 words per chunk
  - Small overlap between consecutive chunks of the same page
  - Never mix unrelated pages
  - Preserve document + page + chunk_id metadata on every chunk
"""

from __future__ import annotations

import re
from typing import List

from core.schemas import Chunk, PageRecord

CHUNK_MAX_WORDS = 500
CHUNK_OVERLAP_WORDS = 50


def _split_words(text: str) -> List[str]:
    """Split text into word tokens (simple whitespace split)."""
    return text.split()


def _words_to_text(words: List[str]) -> str:
    return " ".join(words)


def chunk_page(page: PageRecord) -> List[Chunk]:
    """
    Split one page's text into overlapping chunks.
    Each chunk gets a stable chunk_id: <stem>_p<page>_c<n>.
    """
    doc_stem = re.sub(r"\.[^.]+$", "", page.document)  # strip extension
    words = _split_words(page.text)

    if not words:
        return []

    chunks: List[Chunk] = []
    start = 0
    chunk_idx = 0

    while start < len(words):
        end = min(start + CHUNK_MAX_WORDS, len(words))
        chunk_words = words[start:end]
        chunk_text = _words_to_text(chunk_words)

        chunk_id = f"{doc_stem}_p{page.page:04d}_c{chunk_idx:03d}"
        chunks.append(Chunk(
            chunk_id=chunk_id,
            document=page.document,
            page=page.page,
            text=chunk_text,
            source_type=page.source_type,
        ))

        chunk_idx += 1
        # Advance by (CHUNK_MAX_WORDS - overlap) to create sliding window
        step = CHUNK_MAX_WORDS - CHUNK_OVERLAP_WORDS
        start += step

        if end == len(words):
            break   # last chunk; don't produce empty trailing chunk

    return chunks


def chunk_document(pages: List[PageRecord]) -> List[Chunk]:
    """
    Chunk all pages of a document.
    Returns a flat list of Chunk objects with full metadata.
    """
    all_chunks: List[Chunk] = []
    for page in pages:
        all_chunks.extend(chunk_page(page))
    return all_chunks
