"""Ingestion — a file on disk becomes citable chunks in the store.

    read → chunk → embed → index

Every stage reports rather than throws. A PDF whose pages are scans is indexed
with those pages flagged `needs_ocr` instead of silently contributing nothing;
a document that cannot be embedded is still indexed for keyword search. The
result object says exactly what happened, because "ingested successfully" over
an empty index is the kind of failure that only shows up during a demo.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .chunker import chunk_pages
from .embed import embed_chunks
from .readers import SUPPORTED_SUFFIXES, read_document
from .store import get_store

log = logging.getLogger("prahari.knowledge.ingest")


@dataclass
class IngestResult:
    doc_id: str
    filename: str
    ok: bool
    kind: str = ""
    pages: int = 0
    chunks: int = 0
    embedded: int = 0
    chars: int = 0
    duration_s: float = 0.0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "ok": self.ok,
            "kind": self.kind,
            "pages": self.pages,
            "chunks": self.chunks,
            "embedded": self.embedded,
            "chars": self.chars,
            "duration_s": round(self.duration_s, 2),
            "error": self.error,
            "warnings": self.warnings,
        }


def _doc_id_for(path: Path, digest: str) -> str:
    """Stable id from name plus content, so re-ingesting replaces cleanly."""
    return f"{path.stem[:40]}-{digest[:10]}"


def ingest_file(
    path: str | Path,
    org_id: str = "mrpl",
    embed: bool = True,
) -> IngestResult:
    """Read, chunk, embed and index one file."""
    started = time.perf_counter()
    path = Path(path)

    if not path.exists():
        return IngestResult("", path.name, False, error=f"no such file: {path}")

    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        return IngestResult(
            "", path.name, False,
            error=f"unsupported type '{path.suffix}'. "
                  f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}",
        )

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    doc_id = _doc_id_for(path, digest)
    warnings: list[str] = []

    # --- read ---
    read = read_document(path)
    if read.error:
        return IngestResult(doc_id, path.name, False, error=read.error,
                            duration_s=time.perf_counter() - started)

    ocr_pages = [p.number for p in read.pages if p.needs_ocr]
    if ocr_pages:
        preview = ", ".join(str(n) for n in ocr_pages[:8])
        more = "" if len(ocr_pages) <= 8 else f" (+{len(ocr_pages) - 8} more)"
        warnings.append(
            f"{len(ocr_pages)} page(s) have no extractable text and need OCR: "
            f"{preview}{more}. They are indexed as empty until the OCR cascade "
            f"lands."
        )

    if not read.text.strip():
        return IngestResult(
            doc_id, path.name, False, kind=read.kind,
            pages=len(read.pages),
            error=(
                "no extractable text. This looks like a scanned document or an "
                "image; OCR is not yet wired up (phase P3)."
            ),
            warnings=warnings,
            duration_s=time.perf_counter() - started,
        )

    # --- chunk ---
    chunks = chunk_pages(read.pages, document=path.name)
    if not chunks:
        return IngestResult(doc_id, path.name, False, kind=read.kind,
                            pages=len(read.pages), error="produced no chunks",
                            warnings=warnings,
                            duration_s=time.perf_counter() - started)

    # --- embed (optional; failure degrades to keyword-only) ---
    vectors: list = []
    if embed:
        vectors, embed_error = embed_chunks([c.text for c in chunks])
        if embed_error:
            warnings.append(
                f"embeddings unavailable ({embed_error}); indexed for keyword "
                f"search only"
            )

    # --- index ---
    store = get_store(org_id)
    try:
        store.add_document(
            doc_id=doc_id,
            filename=path.name,
            kind=read.kind,
            chunks=chunks,
            embeddings=vectors or None,
            sha256=digest,
            source_path=str(path),
            pages=len(read.pages),
            meta={"ocr_pending_pages": ocr_pages},
        )
    except Exception as exc:
        return IngestResult(doc_id, path.name, False, kind=read.kind,
                            error=f"indexing failed: {type(exc).__name__}: {exc}",
                            warnings=warnings,
                            duration_s=time.perf_counter() - started)

    return IngestResult(
        doc_id=doc_id,
        filename=path.name,
        ok=True,
        kind=read.kind,
        pages=len(read.pages),
        chunks=len(chunks),
        embedded=len(vectors),
        chars=read.char_count,
        warnings=warnings,
        duration_s=time.perf_counter() - started,
    )


def ingest_directory(
    directory: str | Path,
    org_id: str = "mrpl",
    patterns: list[str] | None = None,
    embed: bool = True,
) -> list[IngestResult]:
    """Index every supported file under a directory.

    This is the "local knowledge base connector" in its simplest form: point it
    at a share, and it walks what is there.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return [IngestResult("", str(directory), False,
                             error=f"not a directory: {directory}")]

    files: list[Path] = []
    for pattern in (patterns or ["**/*"]):
        files.extend(
            p for p in directory.glob(pattern)
            if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
        )

    results: list[IngestResult] = []
    for file_path in sorted(set(files)):
        result = ingest_file(file_path, org_id=org_id, embed=embed)
        results.append(result)
        status = "ok" if result.ok else f"FAILED: {result.error}"
        log.info("ingest %s -> %s", file_path.name, status)
    return results
