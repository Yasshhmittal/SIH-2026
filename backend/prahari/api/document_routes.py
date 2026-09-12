"""Document upload and knowledge-base management.

Uploads land in the organisation's own directory tree and are indexed
immediately, so a file dropped in the UI is searchable by the next question.

Two things are enforced here rather than trusted:

- **Filename sanitisation.** An upload names its own file, and `../../` in that
  name is a path traversal. Only the basename is used, and the resolved path is
  checked for containment.
- **Size limit.** An unbounded upload is a denial-of-service on a laptop.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..config import ORGS_DIR
from ..knowledge.ingest import ingest_directory, ingest_file
from ..knowledge.readers import SUPPORTED_SUFFIXES
from ..knowledge.store import get_store

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 64 * 1024 * 1024      # 64 MB
_UNSAFE = re.compile(r"[^A-Za-z0-9._\- ]")


def _safe_filename(raw: str) -> str:
    """Reduce an arbitrary upload name to a safe basename."""
    name = Path(raw or "upload").name          # discards any directory part
    name = _UNSAFE.sub("_", name).strip(". ")
    return name[:120] or "upload"


def _inbox(org_id: str) -> Path:
    inbox = ORGS_DIR / org_id / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    return inbox


# ----------------------------------------------------------------- upload ---

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    org_id: str = Form("mrpl"),
    embed: bool = Form(True),
) -> dict[str, Any]:
    """Accept a file, store it under the org, index it, and report what happened."""
    filename = _safe_filename(file.filename or "upload")
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"unsupported file type '{suffix or 'none'}'. Supported: "
                f"{', '.join(sorted(SUPPORTED_SUFFIXES))}"
            ),
        )

    inbox = _inbox(org_id)
    target = (inbox / filename).resolve()

    # Containment check: belt and braces after sanitising the name.
    try:
        target.relative_to(inbox.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid filename")

    written = 0
    try:
        with target.open("wb") as sink:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    sink.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"file exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit",
                    )
                sink.write(chunk)
    finally:
        await file.close()

    if written == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="uploaded file is empty")

    result = ingest_file(target, org_id=org_id, embed=embed)

    return {
        "uploaded": {"filename": filename, "bytes": written,
                     "stored_at": f"inbox/{filename}"},
        "ingest": result.to_dict(),
        "kb": get_store(org_id).stats(),
    }


# ---------------------------------------------------------- index a folder ---

class IngestPath(BaseModel):
    path: str
    org_id: str = "mrpl"
    embed: bool = True


@router.post("/ingest-path")
def ingest_path(body: IngestPath) -> dict[str, Any]:
    """Index a file or a whole directory already on this machine.

    This is the knowledge-base connector in its simplest form: point it at a
    share and it walks what is there. Nothing is copied — documents are indexed
    where they already live.
    """
    source = Path(body.path).expanduser()
    if not source.exists():
        raise HTTPException(status_code=404, detail=f"no such path: {source}")

    if source.is_file():
        results = [ingest_file(source, org_id=body.org_id, embed=body.embed)]
    else:
        results = ingest_directory(source, org_id=body.org_id, embed=body.embed)

    succeeded = [r for r in results if r.ok]
    return {
        "path": str(source),
        "files_seen": len(results),
        "files_indexed": len(succeeded),
        "chunks_added": sum(r.chunks for r in succeeded),
        "results": [r.to_dict() for r in results],
        "kb": get_store(body.org_id).stats(),
    }


# ------------------------------------------------------------------ manage ---

@router.get("")
def list_documents(org_id: str = "mrpl") -> dict[str, Any]:
    store = get_store(org_id)
    return {"documents": store.list_documents(), "kb": store.stats()}


@router.get("/stats")
def kb_stats(org_id: str = "mrpl") -> dict[str, Any]:
    return get_store(org_id).stats()


class SearchRequest(BaseModel):
    query: str
    org_id: str = "mrpl"
    k: int = 6


@router.post("/search")
def search_documents(body: SearchRequest) -> dict[str, Any]:
    """Search the index directly, without running an agent task.

    Useful for checking that a freshly uploaded document is actually
    retrievable before asking a question about it.
    """
    from ..knowledge.search import search_knowledge

    observation = search_knowledge(body.query, org_id=body.org_id, k=body.k)
    return {"summary": observation.summary, **observation.data}


@router.delete("/{doc_id}")
def delete_document(doc_id: str, org_id: str = "mrpl") -> dict[str, Any]:
    removed = get_store(org_id).delete_document(doc_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"unknown document: {doc_id}")
    return {"deleted": doc_id, "kb": get_store(org_id).stats()}


@router.post("/clear")
def clear_knowledge_base(org_id: str = "mrpl", delete_files: bool = False) -> dict[str, Any]:
    """Empty the index. Optionally remove the stored uploads too."""
    get_store(org_id).clear()

    files_removed = 0
    if delete_files:
        inbox = _inbox(org_id)
        for item in inbox.iterdir():
            if item.is_file():
                item.unlink()
                files_removed += 1
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)

    return {
        "cleared": True,
        "files_removed": files_removed,
        "kb": get_store(org_id).stats(),
    }
