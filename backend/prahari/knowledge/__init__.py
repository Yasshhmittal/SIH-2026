"""Knowledge plane — local document ingestion and hybrid retrieval.

Nothing here touches the network except Ollama on loopback for embeddings.
"""

from .chunker import Chunk, chunk_pages
from .embed import EMBED_DIM, EMBED_MODEL, EmbeddingUnavailable, embed_query, embed_texts
from .ingest import IngestResult, ingest_directory, ingest_file
from .readers import SUPPORTED_SUFFIXES, Page, ReadResult, read_document
from .search import search_knowledge
from .store import Hit, KnowledgeStore, get_store

__all__ = [
    "Chunk", "chunk_pages",
    "Page", "ReadResult", "read_document", "SUPPORTED_SUFFIXES",
    "EMBED_MODEL", "EMBED_DIM", "EmbeddingUnavailable", "embed_texts", "embed_query",
    "IngestResult", "ingest_file", "ingest_directory",
    "KnowledgeStore", "Hit", "get_store",
    "search_knowledge",
]
