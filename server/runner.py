"""
server/runner.py — Workflow orchestration for the PRAHARÍ backend.

Wraps the existing, working NEBULA pipeline (core.agent.run_agent) and the RAG
components without modifying them. Each workflow runs in a background thread and
pushes frontend events through the `emit` callback.

Workflows:
  - run_inspection : full grounded pipeline → findings + citations + DOCX
  - run_search     : BGE-M3 semantic retrieval across the SOP knowledge base
(the coding workflow lives in server/coding_agent.py)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, List, Optional

from server.events import make, translate

# Sample fallbacks (same documents the Streamlit UI uses).
SAMPLE_INSPECTION = Path("data/inspection/inspection_report.pdf")
SAMPLE_SOP = Path("data/knowledge/SOP_MAINT_017.pdf")
KNOWLEDGE_DIR = Path("data/knowledge")


# ── Shared helpers ──────────────────────────────────────────────────────────

def ensure_sample_docs() -> tuple[str, str]:
    """Guarantee the sample inspection + SOP PDFs exist; regenerate if missing."""
    if not (SAMPLE_INSPECTION.exists() and SAMPLE_SOP.exists()):
        from scripts.test_pipeline import create_test_pdfs
        create_test_pdfs()
    return str(SAMPLE_INSPECTION), str(SAMPLE_SOP)


def _sources(retrieved) -> List[dict]:
    """RetrievedChunk[] → frontend source cards [{document, section, page, score}]."""
    out = []
    for rc in retrieved:
        snippet = " ".join(rc.chunk.text.split())
        section = (snippet[:60] + "…") if len(snippet) > 60 else (snippet or rc.chunk.chunk_id)
        out.append({
            "document": rc.chunk.document,
            "section": section,
            "page": rc.chunk.page,
            "score": round(float(rc.score), 4),
        })
    return out


def _claims(claim_list) -> List[dict]:
    return [{
        "claim": c.claim,
        "status": c.status,
        "sources": [
            {"document": s.document, "page": s.page, "evidence": s.evidence}
            for s in c.sources
        ],
    } for c in claim_list]


def _analysis(reasoning) -> Optional[dict]:
    if not reasoning:
        return None
    return {
        "task_class": reasoning.task_class,
        "supported_findings": _claims(reasoning.supported_findings),
        "inferences": _claims(reasoning.inferences),
        "uncertainties": _claims(reasoning.uncertainties),
        "recommended_action": reasoning.recommended_action,
    }


def _validation(v) -> Optional[dict]:
    if not v:
        return None
    return {
        "passed": v.passed,
        "unsupported_count": v.unsupported_count,
        "invalid_citations": v.invalid_citations,
        "missing_evidence": v.missing_evidence,
        "warnings": v.warnings,
        "failure_reason": v.failure_reason,
    }


# ── Inspection workflow ─────────────────────────────────────────────────────

def run_inspection(task: str, inspection_path: Optional[str],
                   sop_path: Optional[str], emit: Callable[[dict], None]) -> None:
    """Full grounded inspection pipeline. Falls back to sample docs if needed."""
    from core.agent import run_agent

    # Resolve inputs: uploaded inspection PDF + server-side SOP; sample fallback.
    sample_insp, sample_sop = None, None
    if not inspection_path or not sop_path:
        sample_insp, sample_sop = ensure_sample_docs()
    inspection_path = inspection_path or sample_insp
    sop_path = sop_path or sample_sop

    emit(make("started", "profile", "Inspection Analyst initialised.", {
        "profile": {
            "name": "Inspection Analyst",
            "model": "Qwen2.5-7B · BGE-M3 · PaddleOCR",
            "mode": "Grounded RAG",
        }
    }))

    def cb(msg: str) -> None:
        emit(translate(msg))

    state = run_agent(task=task, inspection_path=inspection_path,
                      sop_path=sop_path, progress_callback=cb)

    profile = {
        "name": "Inspection Analyst",
        "model": "Qwen2.5-7B · BGE-M3 · PaddleOCR",
        "mode": state.reasoning.task_class if state.reasoning else "Grounded RAG",
    }
    sources = _sources(state.retrieved)
    analysis = _analysis(state.reasoning)
    validation = _validation(state.validation)
    artifact = Path(state.docx_path).name if state.docx_path else None

    if state.error:
        emit(make("error", "complete", f"Pipeline error: {state.error}", {
            "profile": profile, "sources": sources,
            "analysis": analysis, "validation": validation,
        }))
        return

    if artifact:
        msg = "Analysis complete — approval note generated."
    elif validation and validation.get("missing_evidence"):
        msg = "Insufficient SOP evidence — the agent refused to fabricate a note."
    elif validation and not validation.get("passed"):
        msg = "Analysis complete — validation flagged issues; no note generated."
    else:
        msg = "Analysis complete."

    data = {"profile": profile, "sources": sources,
            "analysis": analysis, "validation": validation}
    if artifact:
        data["artifact"] = artifact
    emit(make("completed", "complete", msg, data))


# ── Search workflow ─────────────────────────────────────────────────────────

def run_search(task: str, emit: Callable[[dict], None]) -> None:
    """Semantic retrieval over every PDF in the SOP knowledge base."""
    emit(make("started", "profile", "Document Retriever initialised.", {
        "profile": {"name": "Document Retriever", "model": "BGE-M3", "mode": "Semantic Search"}
    }))

    pdfs = sorted(KNOWLEDGE_DIR.glob("*.pdf"))
    if not pdfs:
        ensure_sample_docs()
        pdfs = sorted(KNOWLEDGE_DIR.glob("*.pdf"))

    if not pdfs:
        emit(make("error", "complete", "No knowledge-base documents found to search.", {}))
        return

    from document.loader import load_pdf
    from document.chunker import chunk_document
    from rag.index import build_or_load_index

    emit(make("started", "search", f"Indexing knowledge base ({len(pdfs)} document(s))…", {}))
    indices = []
    total_chunks = 0
    for pdf in pdfs:
        try:
            pages = load_pdf(str(pdf), run_ocr=True)
            chunks = chunk_document(pages)
            matrix, chunk_list = build_or_load_index(chunks, str(pdf))
            indices.append((matrix, chunk_list))
            total_chunks += len(chunk_list)
        except Exception as exc:
            emit(make("failed", "search", f"Skipped {pdf.name}: {exc}", {}))

    emit(make("completed", "search",
              f"Indexed {total_chunks} chunks across {len(indices)} document(s).", {}))

    if not indices:
        emit(make("error", "complete", "Knowledge base could not be indexed.", {}))
        return

    emit(make("started", "retrieval", "Searching for relevant passages…", {}))
    from rag.retrieve import retrieve_top_k
    from models.bge import BGE

    bge = BGE()
    merged = []
    try:
        for matrix, chunk_list in indices:
            merged.extend(retrieve_top_k(task, matrix, chunk_list, bge, k=5))
    finally:
        bge.unload()

    merged.sort(key=lambda r: r.score, reverse=True)
    top = merged[:6]
    sources = _sources(top)
    results = [{
        "document": r.chunk.document,
        "page": r.chunk.page,
        "score": round(float(r.score), 4),
        "snippet": " ".join(r.chunk.text.split())[:400],
    } for r in top]

    emit(make("completed", "retrieval", f"Found {len(top)} relevant passage(s).",
              {"sources": sources}))
    emit(make("completed", "complete", "Search complete.", {
        "sources": sources,
        "search_results": results,
        "profile": {"name": "Document Retriever", "model": "BGE-M3", "mode": "Semantic Search"},
    }))
