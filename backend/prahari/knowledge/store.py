"""Knowledge store — SQLite + numpy, hybrid retrieval, no external service.

Qdrant was the original plan, and it would need Docker running. For an
air-gapped product that is a real cost: another service to install, start,
health-check and explain. SQLite is already a dependency, ships in the standard
library, and stores the corpus in one file per organisation.

Retrieval is genuinely hybrid:

- **Sparse (BM25)** catches exact terms — "8-P-1204", "6.4 mm", a clause number.
  Embeddings are unreliable on identifiers, and identifiers are most of what an
  engineer searches for.
- **Dense (bge-m3 via Ollama, CPU)** catches paraphrase — "how thin is too thin"
  finding a passage about retirement thickness.
- **RRF** fuses the two rankings without needing their scores to be comparable.

Everything is scoped by `org_id`: one company's chunks are structurally
unreachable from another's, which is what makes a single deployment safe to
share between the demo orgs.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..config import ORGS_DIR

# BM25 parameters. Defaults from the literature; k1 controls term-frequency
# saturation, b controls length normalisation.
_K1 = 1.5
_B = 0.75

_TOKEN = re.compile(r"[a-z0-9][a-z0-9\-\.]*", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Lowercase tokens, keeping hyphens and dots so '8-P-1204' and '6.4'
    survive as single terms. Splitting those is what makes keyword search fail
    on exactly the queries engineers type."""
    return [t.lower() for t in _TOKEN.findall(text or "")]


# Relevance floor, calibrated against bge-m3 on this corpus.
#
# bge-m3 has a high similarity baseline: unrelated text still scores 0.42-0.47,
# while genuinely relevant passages reach 0.55-0.69. A threshold below ~0.52
# therefore admits pure noise. Measured with scripts/check_floor.py — re-run it
# if the embedding model changes, because these numbers are model-specific.
MIN_DENSE_SIMILARITY = 0.52

# Very common words are not evidence of relevance on their own. "temperature"
# appears in an insulation clause and in a catalyst question alike, so a single
# shared generic term must not keep a chunk alive.
_WEAK_TERMS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "been", "by", "do",
    "does", "for", "from", "has", "have", "how", "i", "in", "is", "it", "its",
    "may", "must", "not", "of", "on", "or", "shall", "should", "that", "the",
    "their", "then", "there", "this", "to", "was", "we", "what", "when",
    "where", "which", "who", "why", "will", "with", "would",
    # domain words so ubiquitous in this corpus that they carry no signal
    "data", "document", "inspection", "mm", "per", "procedure", "refinery",
    "report", "service", "shall", "system", "temperature", "unit", "year",
    "years",
}


def significant_terms(text: str) -> set[str]:
    """Tokens that actually discriminate: drop stopwords and bare digits."""
    return {
        t for t in tokenize(text)
        if t not in _WEAK_TERMS and len(t) > 1 and not t.isdigit()
    }


@dataclass
class Hit:
    chunk_id: int
    document: str
    doc_id: str
    page: int
    section: str
    text: str
    score: float
    dense_rank: int | None = None
    sparse_rank: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document": self.document,
            "doc_id": self.doc_id,
            "page": self.page,
            "section": self.section,
            "text": self.text,
            "score": round(self.score, 4),
            "dense_rank": self.dense_rank,
            "sparse_rank": self.sparse_rank,
        }


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    kind        TEXT,
    sha256      TEXT,
    pages       INTEGER,
    chars       INTEGER,
    source_path TEXT,
    ingested_at REAL,
    meta        TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id     TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    page       INTEGER,
    section    TEXT,
    text       TEXT NOT NULL,
    tokens     INTEGER,
    embedding  BLOB,
    meta       TEXT
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);

-- Inverted index for BM25. Kept explicit rather than using FTS5 so the
-- scoring is visible and tunable.
CREATE TABLE IF NOT EXISTS postings (
    term     TEXT NOT NULL,
    chunk_id INTEGER NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    tf       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_postings_term ON postings(term);
CREATE INDEX IF NOT EXISTS idx_postings_chunk ON postings(chunk_id);
"""


class KnowledgeStore:
    """One SQLite file per organisation."""

    _locks: dict[str, threading.RLock] = {}

    def __init__(self, org_id: str = "mrpl") -> None:
        self.org_id = org_id
        self.path = ORGS_DIR / org_id / "kb" / "knowledge.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = KnowledgeStore._locks.setdefault(org_id, threading.RLock())
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(SCHEMA)

    # -- writing -----------------------------------------------------------

    def add_document(
        self,
        doc_id: str,
        filename: str,
        kind: str,
        chunks: list[Any],
        embeddings: list[np.ndarray] | None = None,
        sha256: str = "",
        source_path: str = "",
        pages: int = 0,
        meta: dict[str, Any] | None = None,
    ) -> int:
        """Insert a document and its chunks. Replaces any existing doc_id."""
        import time

        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.execute(
                "INSERT INTO documents (doc_id, filename, kind, sha256, pages, "
                "chars, source_path, ingested_at, meta) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (doc_id, filename, kind, sha256, pages,
                 sum(len(c.text) for c in chunks), source_path, time.time(),
                 json.dumps(meta or {})),
            )

            for position, chunk in enumerate(chunks):
                blob = None
                if embeddings is not None and position < len(embeddings):
                    vector = np.asarray(embeddings[position], dtype=np.float32)
                    norm = np.linalg.norm(vector)
                    if norm > 0:
                        vector = vector / norm     # store normalised: dot == cosine
                    blob = vector.tobytes()

                tokens = tokenize(chunk.text)
                cursor = conn.execute(
                    "INSERT INTO chunks (doc_id, page, section, text, tokens, "
                    "embedding, meta) VALUES (?,?,?,?,?,?,?)",
                    (doc_id, chunk.page, chunk.section, chunk.text,
                     len(tokens), blob, json.dumps(chunk.meta)),
                )
                chunk_id = cursor.lastrowid

                conn.executemany(
                    "INSERT INTO postings (term, chunk_id, tf) VALUES (?,?,?)",
                    [(term, chunk_id, count)
                     for term, count in Counter(tokens).items()],
                )

        return len(chunks)

    def delete_document(self, doc_id: str) -> bool:
        with self._lock, self._connect() as conn:
            # Postings reference chunks, which cascade from documents; delete
            # postings explicitly since SQLite cascades one level at a time.
            conn.execute(
                "DELETE FROM postings WHERE chunk_id IN "
                "(SELECT chunk_id FROM chunks WHERE doc_id = ?)", (doc_id,)
            )
            cursor = conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            return cursor.rowcount > 0

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                "DELETE FROM postings; DELETE FROM chunks; DELETE FROM documents;"
            )

    # -- reading -----------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            docs = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
            chunks = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
            embedded = conn.execute(
                "SELECT COUNT(*) AS n FROM chunks WHERE embedding IS NOT NULL"
            ).fetchone()["n"]
            return {
                "org_id": self.org_id,
                "documents": docs,
                "chunks": chunks,
                "embedded_chunks": embedded,
                "path": str(self.path),
            }

    def list_documents(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT d.*, COUNT(c.chunk_id) AS chunk_count "
                "FROM documents d LEFT JOIN chunks c ON c.doc_id = d.doc_id "
                "GROUP BY d.doc_id ORDER BY d.ingested_at DESC"
            ).fetchall()
            return [
                {
                    "doc_id": r["doc_id"],
                    "filename": r["filename"],
                    "kind": r["kind"],
                    "pages": r["pages"],
                    "chars": r["chars"],
                    "chunks": r["chunk_count"],
                    "ingested_at": r["ingested_at"],
                    "meta": json.loads(r["meta"] or "{}"),
                }
                for r in rows
            ]

    # -- search ------------------------------------------------------------

    def _bm25(self, conn: sqlite3.Connection, query: str, limit: int) -> list[tuple[int, float]]:
        terms = tokenize(query)
        if not terms:
            return []

        total = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
        if not total:
            return []

        avg_len = conn.execute(
            "SELECT AVG(tokens) AS a FROM chunks"
        ).fetchone()["a"] or 1.0

        scores: dict[int, float] = {}
        for term in set(terms):
            rows = conn.execute(
                "SELECT p.chunk_id, p.tf, c.tokens FROM postings p "
                "JOIN chunks c ON c.chunk_id = p.chunk_id WHERE p.term = ?",
                (term,),
            ).fetchall()
            if not rows:
                continue

            df = len(rows)
            idf = math.log(1 + (total - df + 0.5) / (df + 0.5))

            for row in rows:
                tf, length = row["tf"], row["tokens"] or 1
                denominator = tf + _K1 * (1 - _B + _B * length / avg_len)
                scores[row["chunk_id"]] = scores.get(row["chunk_id"], 0.0) + \
                    idf * (tf * (_K1 + 1)) / denominator

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[:limit]

    def _dense(
        self, conn: sqlite3.Connection, query_vector: np.ndarray, limit: int
    ) -> list[tuple[int, float]]:
        rows = conn.execute(
            "SELECT chunk_id, embedding FROM chunks WHERE embedding IS NOT NULL"
        ).fetchall()
        if not rows:
            return []

        query_vector = np.asarray(query_vector, dtype=np.float32)
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = query_vector / norm

        ids = np.empty(len(rows), dtype=np.int64)
        matrix = np.empty((len(rows), query_vector.shape[0]), dtype=np.float32)
        usable = 0
        for row in rows:
            vector = np.frombuffer(row["embedding"], dtype=np.float32)
            if vector.shape[0] != query_vector.shape[0]:
                continue        # a stale index from a different embedding model
            ids[usable] = row["chunk_id"]
            matrix[usable] = vector
            usable += 1

        if not usable:
            return []

        similarities = matrix[:usable] @ query_vector
        order = np.argsort(-similarities)[:limit]
        return [(int(ids[i]), float(similarities[i])) for i in order]

    def search(
        self,
        query: str,
        k: int = 6,
        query_vector: np.ndarray | None = None,
        rrf_k: int = 60,
        min_dense_similarity: float = MIN_DENSE_SIMILARITY,
        require_term_overlap: bool = True,
    ) -> list[Hit]:
        """Hybrid retrieval with Reciprocal Rank Fusion, plus a relevance floor.

        RRF scores by *rank*, not by raw score, so BM25 and cosine values never
        have to be made comparable — which is the usual source of a badly tuned
        hybrid search.

        The floor matters as much as the fusion. RRF always ranks *something*,
        so an unrelated query ("catalyst regeneration temperature profile"
        against a piping corpus) otherwise returns three confident-looking hits
        that support nothing. A chunk survives only if it clears a real dense
        similarity or shares a *discriminating* term with the query.
        Retrieving nothing is a valid, honest answer.
        """
        pool = max(k * 4, 20)
        query_terms = significant_terms(query)

        with self._lock, self._connect() as conn:
            sparse = self._bm25(conn, query, pool)
            dense = (self._dense(conn, query_vector, pool)
                     if query_vector is not None else [])

            dense_scores = dict(dense)
            sparse_rank = {cid: i + 1 for i, (cid, _) in enumerate(sparse)}
            dense_rank = {cid: i + 1 for i, (cid, _) in enumerate(dense)}

            fused: dict[int, float] = {}
            for cid, rank in sparse_rank.items():
                fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank)
            for cid, rank in dense_rank.items():
                fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank)

            if not fused:
                return []

            ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)

            # Apply the floor before truncating to k, so a weak-but-relevant
            # chunk is not displaced by a strong-but-irrelevant one.
            candidate_ids = [cid for cid, _ in ordered[:pool]]
            placeholders = ",".join("?" * len(candidate_ids))
            rows = conn.execute(
                f"SELECT c.chunk_id, c.page, c.section, c.text, c.doc_id, "
                f"d.filename FROM chunks c JOIN documents d ON d.doc_id = c.doc_id "
                f"WHERE c.chunk_id IN ({placeholders})",
                candidate_ids,
            ).fetchall()

        by_id = {r["chunk_id"]: r for r in rows}

        hits: list[Hit] = []
        for cid, score in ordered:
            row = by_id.get(cid)
            if row is None:
                continue

            similarity = dense_scores.get(cid)
            dense_ok = similarity is not None and similarity >= min_dense_similarity
            overlap_ok = (
                not require_term_overlap
                or bool(query_terms & significant_terms(row["text"]))
            )

            # Keep a chunk if either signal vouches for it. A strong dense
            # match with no shared vocabulary is exactly the paraphrase case
            # hybrid search exists to catch, so dense alone is sufficient.
            if not (dense_ok or overlap_ok):
                continue

            hits.append(Hit(
                chunk_id=cid,
                document=row["filename"],
                doc_id=row["doc_id"],
                page=row["page"] or 1,
                section=row["section"] or "",
                text=row["text"],
                score=score,
                dense_rank=dense_rank.get(cid),
                sparse_rank=sparse_rank.get(cid),
            ))
            if len(hits) >= k:
                break

        return hits


_stores: dict[str, KnowledgeStore] = {}
_stores_lock = threading.Lock()


def get_store(org_id: str = "mrpl") -> KnowledgeStore:
    with _stores_lock:
        if org_id not in _stores:
            _stores[org_id] = KnowledgeStore(org_id)
        return _stores[org_id]
