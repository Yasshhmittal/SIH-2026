"""Retrieval for the agent's kb.search tool.

Returns chunks *and* a citation list, because the DOCX renderer consumes
citations directly. The contract is the same one the stub honoured, so nothing
upstream changes — the recipe's `{"$from_step": 1, "path": "data.citations"}`
reference keeps working.
"""

from __future__ import annotations

from typing import Any

from ..agent.schemas import Observation
from .embed import embed_query
from .store import get_store


def search_knowledge(
    query: str,
    org_id: str = "mrpl",
    k: int = 6,
) -> Observation:
    """Hybrid search over the organisation's indexed documents."""
    store = get_store(org_id)
    stats = store.stats()

    if stats["chunks"] == 0:
        # An empty index is a setup problem, not a search failure. Say so
        # plainly rather than returning zero hits as though nothing matched.
        return Observation(
            ok=True,
            summary="knowledge base is empty — no documents indexed yet",
            data={
                "query": query,
                "chunks": [],
                "citations": [],
                "empty_index": True,
                "hint": (
                    "Upload a document, or POST /api/documents/ingest-path "
                    "with a folder to index."
                ),
            },
        )

    query_vector = embed_query(query)
    hits = store.search(query, k=k, query_vector=query_vector)

    if not hits:
        return Observation(
            ok=True,
            summary=f"no matches for {query[:60]!r} across "
                    f"{stats['documents']} document(s)",
            data={"query": query, "chunks": [], "citations": [],
                  "searched_documents": stats["documents"]},
        )

    chunks: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    for position, hit in enumerate(hits, start=1):
        label = f"C{position}"
        chunks.append({
            "id": label,
            "document": hit.document,
            "doc_id": hit.doc_id,
            "page": hit.page,
            "section": hit.section,
            "text": hit.text,
            "score": round(hit.score, 4),
            "dense_rank": hit.dense_rank,
            "sparse_rank": hit.sparse_rank,
        })
        citations.append({
            "id": label,
            "document": hit.document,
            "page": hit.page,
            "section": hit.section,
        })

    retrieval = "hybrid (BM25 + dense)" if query_vector is not None else "BM25 only"
    chunk_texts = [f"[{c['id']}: {c['document']}] {c['text']}" for c in chunks]
    return Observation(
        ok=True,
        summary=f"retrieved {len(hits)} chunk(s) via {retrieval} from "
                f"{stats['documents']} document(s)",
        data={
            "query": query,
            "chunks": chunks,
            "chunk_texts": chunk_texts,
            "citations": citations,
            "retrieval": retrieval,
            "searched_documents": stats["documents"],
        },
    )
