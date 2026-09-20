"""
core/agent.py — Bounded task workflow controller for NEBULA.

Executes the fixed pipeline:
  RECEIVE → CLASSIFY → PLAN → OCR/VISION → RETRIEVE → REASON → VALIDATE → FINALIZE

Each step is a known component call — no arbitrary tool use, no self-modification.
Sequential execution: only one model loaded at a time (M4 memory constraint).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Optional

from core.schemas import AgentState, ValidationResult
from core.router import classify_document, build_component_plan
from core.validator import validate_retrieval, validate_reasoning


# ── Logging ───────────────────────────────────────────────────────────────────

LOGS_DIR = Path(os.getenv("LOGS_DIR", "./logs"))


def _log_event(state: AgentState, msg: str, callback: Optional[Callable] = None) -> None:
    """Append event to state timeline and optional UI callback."""
    state.log(msg)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOGS_DIR / "events.jsonl", "a") as f:
        import datetime
        f.write(json.dumps({"ts": datetime.datetime.utcnow().isoformat(), "event": msg}) + "\n")
    if callback:
        callback(msg)


# ── Agent controller ──────────────────────────────────────────────────────────

def run_agent(
    task: str,
    inspection_path: str,
    sop_path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> AgentState:
    """
    Execute the full NEBULA agent pipeline.

    Args:
        task:               Natural-language task description from user.
        inspection_path:    Path to the uploaded inspection report PDF.
        sop_path:           Path to the SOP PDF for retrieval.
        progress_callback:  Optional function(msg) called at each step for UI updates.

    Returns:
        AgentState with all intermediate and final results populated.
    """
    state = AgentState(
        task=task,
        inspection_path=inspection_path,
        sop_path=sop_path,
    )

    def log(msg: str) -> None:
        _log_event(state, msg, progress_callback)

    # ── STEP 1: CLASSIFY ─────────────────────────────────────────────────────
    log("⚙️  CLASSIFY — Analysing document type...")
    try:
        doc_info = classify_document(inspection_path)
        plan = build_component_plan(doc_info)
        state.doc_info = doc_info
        state.router_plan = plan
        state.log(f"  Task class: {doc_info['task_class']}")
        state.log(f"  Pages: {doc_info['page_count']} | OCR needed: {plan['use_ocr']} | Vision: {plan['use_vision']}")
        log(f"✅ CLASSIFY — {doc_info['task_class']} | {doc_info['page_count']} pages | Vision: {plan['use_vision']}")
    except Exception as exc:
        state.error = f"CLASSIFY failed: {exc}"
        log(f"❌ CLASSIFY failed: {exc}")
        return state

    # ── STEP 2: OCR / DOCUMENT EXTRACTION ────────────────────────────────────
    log("📄 OCR — Extracting document text...")
    try:
        from document.loader import load_pdf
        from document.ocr import run_ocr_on_page

        pages = load_pdf(inspection_path, run_ocr=plan["use_ocr"])
        state.pages = pages
        log(f"✅ OCR — {len(pages)} pages extracted")
    except Exception as exc:
        state.error = f"OCR/extraction failed: {exc}"
        log(f"❌ OCR failed: {exc}")
        return state

    # ── STEP 3: VISION (conditional) ─────────────────────────────────────────
    if plan["use_vision"]:
        log("🔍 VISION — Running Qwen2.5-VL on visual pages...")
        try:
            from models.qwen_vl import QwenVL
            vl = QwenVL()
            visual_count = 0
            for page in state.pages:
                if page.image_path:
                    observations = vl.analyze_page(page)
                    page.visual_observations = observations
                    visual_count += len(observations)
            vl.unload()  # release memory before loading next model
            log(f"✅ VISION — {visual_count} visual observations extracted")
        except Exception as exc:
            log(f"⚠️  VISION skipped (non-critical): {exc}")
            # Visual step is non-critical; continue pipeline
    else:
        log("⏭️  VISION — No visual content detected; step skipped")

    # ── STEP 4: CHUNK + INDEX SOP ────────────────────────────────────────────
    log("📚 RETRIEVAL — Loading SOP index...")
    try:
        from document.chunker import chunk_document
        from rag.index import build_or_load_index

        sop_pages = load_pdf(sop_path, run_ocr=True)
        sop_chunks = chunk_document(sop_pages)
        embedding_matrix, chunk_list = build_or_load_index(sop_chunks, sop_path)
        state.chunks = chunk_list
        log(f"✅ RETRIEVAL — SOP indexed: {len(chunk_list)} chunks")
    except Exception as exc:
        state.error = f"SOP indexing failed: {exc}"
        log(f"❌ RETRIEVAL index failed: {exc}")
        return state

    # ── STEP 5: RETRIEVE TOP-K ────────────────────────────────────────────────
    log("🔎 RETRIEVAL — Finding relevant SOP evidence...")
    try:
        from rag.retrieve import retrieve_top_k
        from models.bge import BGE

        # Build query from task + key findings from OCR text
        doc_text_summary = " ".join(p.text[:200] for p in state.pages[:3])
        query = f"{task}\n\nObserved document content: {doc_text_summary}"

        bge = BGE()
        retrieved = retrieve_top_k(query, embedding_matrix, chunk_list, bge, k=3)
        bge.unload()

        # Check retrieval threshold (mechanism 3)
        ok, reason = validate_retrieval(retrieved)
        if not ok:
            log(f"❌ RETRIEVAL — {reason}")
            state.validation = ValidationResult(
                passed=False,
                missing_evidence=True,
                failure_reason=reason,
            )
            return state

        state.retrieved = retrieved
        sources = [f"{r.chunk.document} p.{r.chunk.page} ({r.score:.2f})" for r in retrieved]
        log(f"✅ RETRIEVAL — Top {len(retrieved)} chunks: {', '.join(sources)}")
    except Exception as exc:
        state.error = f"Retrieval failed: {exc}"
        log(f"❌ RETRIEVAL failed: {exc}")
        return state

    # ── STEP 6: REASON ───────────────────────────────────────────────────────
    log("🧠 REASONING — Qwen2.5-7B grounded analysis...")
    try:
        from models.qwen_text import QwenText
        qwen = QwenText()
        reasoning_result = qwen.reason(task, state.pages, state.retrieved)
        qwen.unload()
        state.reasoning = reasoning_result
        log(f"✅ REASONING — {len(reasoning_result.supported_findings)} supported findings | "
            f"{len(reasoning_result.uncertainties)} uncertainties")
    except Exception as exc:
        state.error = f"Reasoning failed: {exc}"
        log(f"❌ REASONING failed: {exc}")
        return state

    # ── STEP 7: VALIDATE ─────────────────────────────────────────────────────
    log("✔️  VALIDATION — Checking grounding and citations...")
    try:
        validation = validate_reasoning(state.reasoning, state.retrieved, state.pages)
        state.validation = validation
        if validation.passed:
            log(f"✅ VALIDATION — Passed | Unsupported: {validation.unsupported_count}")
        else:
            log(f"⚠️  VALIDATION — Failed: {validation.failure_reason}")
    except Exception as exc:
        state.error = f"Validation failed: {exc}"
        log(f"❌ VALIDATION failed: {exc}")
        return state

    # ── STEP 8: FINALIZE / DOCX ──────────────────────────────────────────────
    if state.validation and state.validation.passed:
        log("📝 DOCX — Generating approval note...")
        try:
            from artifacts.docx import generate_approval_note
            output_dir = Path(os.getenv("ARTIFACTS_OUTPUT_DIR", "./output"))
            output_dir.mkdir(parents=True, exist_ok=True)
            docx_path = generate_approval_note(state, output_dir)
            state.docx_path = docx_path
            log(f"✅ DOCX — Saved: {docx_path}")
        except Exception as exc:
            log(f"❌ DOCX generation failed: {exc}")
    else:
        log("🚫 DOCX skipped — validation did not pass. Explicit insufficiency noted.")

    log("🏁 Agent pipeline complete.")
    return state
