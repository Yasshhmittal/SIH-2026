"""
artifacts/docx.py — Approval-note DOCX generator for NEBULA.

Sections (from plan §7, 130–165 minutes):
  Title
  Equipment / Report
  Executive Summary
  Observed Findings
  SOP Evidence
  Grounded Analysis
  Inference / Uncertainty
  Recommended Action
  Limitations
  AI-DRAFTED — HUMAN REVIEW REQUIRED  ← always present
"""

from __future__ import annotations

import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from core.schemas import AgentState


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def _add_body(doc: Document, text: str) -> None:
    doc.add_paragraph(text)


def _add_warning_box(doc: Document, text: str) -> None:
    """Add a visually distinct paragraph for the HUMAN REVIEW disclaimer."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)


def generate_approval_note(state: AgentState, output_dir: Path) -> str:
    """
    Generate the approval-note DOCX from a completed AgentState.

    Returns:
        Absolute path to the generated .docx file.
    """
    doc = Document()

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_title = f"NEBULA Approval Note — {ts}"

    # ── Title ──────────────────────────────────────────────────────────────
    _add_heading(doc, "NEBULA / PRAHARÍ — AI-Drafted Approval Note", level=1)
    _add_body(doc, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _add_body(doc, f"Task: {state.task}")

    doc.add_paragraph()

    # ── AI REVIEW DISCLAIMER (prominent, top) ─────────────────────────────
    _add_warning_box(doc, "⚠  AI-DRAFTED — HUMAN REVIEW REQUIRED  ⚠")
    _add_body(
        doc,
        "This document was produced by a local AI system (NEBULA prototype). "
        "It is decision support, not an authoritative engineering judgement. "
        "A qualified human reviewer must verify all findings before acting."
    )
    doc.add_paragraph()

    # ── Document / Equipment ───────────────────────────────────────────────
    _add_heading(doc, "1. Documents Analysed", level=2)
    if state.inspection_path:
        _add_body(doc, f"• Inspection Report: {Path(state.inspection_path).name}")
    if state.sop_path:
        _add_body(doc, f"• SOP Reference: {Path(state.sop_path).name}")

    # ── Executive Summary ─────────────────────────────────────────────────
    _add_heading(doc, "2. Executive Summary", level=2)
    reasoning = state.reasoning
    if reasoning:
        n_supported = len(reasoning.supported_findings)
        n_inferences = len(reasoning.inferences)
        n_uncertain = len(reasoning.uncertainties)
        _add_body(
            doc,
            f"The local AI agent identified {n_supported} supported finding(s), "
            f"{n_inferences} inference(s), and {n_uncertain} uncertainty/uncertainties. "
            f"Recommended action: {reasoning.recommended_action or 'See section 6.'}"
        )
    else:
        _add_body(doc, "No reasoning output available.")

    # ── Observed Findings ─────────────────────────────────────────────────
    _add_heading(doc, "3. Observed Document Findings", level=2)
    page_count = len(state.pages)
    _add_body(doc, f"Pages processed: {page_count}")
    for page in state.pages[:10]:   # cap at 10 pages in DOCX for brevity
        p_label = f"[{page.document} · Page {page.page} · {page.source_type}"
        if page.ocr_confidence is not None:
            p_label += f" · OCR conf: {page.ocr_confidence:.2f}"
        p_label += "]"
        _add_body(doc, p_label)
        _add_body(doc, page.text[:500] + ("…" if len(page.text) > 500 else ""))
        if page.visual_observations:
            for vo in page.visual_observations:
                _add_body(doc, f"  Visual [{vo.confidence}]: {vo.text}")
        doc.add_paragraph()

    # ── SOP Evidence ──────────────────────────────────────────────────────
    _add_heading(doc, "4. Retrieved SOP Evidence", level=2)
    if state.retrieved:
        for rc in state.retrieved:
            _add_body(doc, f"[{rc.chunk.document} · Page {rc.chunk.page} · Score: {rc.score:.3f}]")
            _add_body(doc, rc.chunk.text[:400] + ("…" if len(rc.chunk.text) > 400 else ""))
            doc.add_paragraph()
    else:
        _add_body(doc, "No SOP evidence retrieved.")

    # ── Grounded Analysis ─────────────────────────────────────────────────
    _add_heading(doc, "5. Grounded Analysis — Supported Findings", level=2)
    if reasoning and reasoning.supported_findings:
        for i, claim in enumerate(reasoning.supported_findings, 1):
            _add_body(doc, f"{i}. [SUPPORTED FACT] {claim.claim}")
            for src in claim.sources:
                _add_body(doc, f"   Source: {src.document} · Page {src.page}")
                _add_body(doc, f"   Evidence: {src.evidence[:200]}")
    else:
        _add_body(doc, "No supported findings established.")

    # ── Inferences + Uncertainties ────────────────────────────────────────
    _add_heading(doc, "6. Inferences and Uncertainties", level=2)
    if reasoning and reasoning.inferences:
        _add_body(doc, "INFERENCES:")
        for i, claim in enumerate(reasoning.inferences, 1):
            _add_body(doc, f"{i}. [INFERENCE] {claim.claim}")
            for src in claim.sources:
                _add_body(doc, f"   Source: {src.document} · Page {src.page}")

    if reasoning and reasoning.uncertainties:
        _add_body(doc, "UNCERTAINTIES / MISSING INFORMATION:")
        for i, claim in enumerate(reasoning.uncertainties, 1):
            _add_body(doc, f"{i}. [UNCERTAINTY] {claim.claim}")

    # ── Recommended Action ────────────────────────────────────────────────
    _add_heading(doc, "7. Recommended Action", level=2)
    action = reasoning.recommended_action if reasoning else ""
    _add_body(doc, action if action else "Cannot determine from the provided evidence.")

    # ── Validation Summary ────────────────────────────────────────────────
    _add_heading(doc, "8. Validation Summary", level=2)
    if state.validation:
        v = state.validation
        _add_body(doc, f"Validation passed: {v.passed}")
        _add_body(doc, f"Unsupported claims flagged: {v.unsupported_count}")
        if v.warnings:
            _add_body(doc, "Warnings:")
            for w in v.warnings:
                _add_body(doc, f"  • {w}")
    else:
        _add_body(doc, "Validation not performed.")

    # ── Limitations ───────────────────────────────────────────────────────
    _add_heading(doc, "9. Limitations", level=2)
    _add_body(doc, (
        "• This analysis is based solely on the uploaded documents and retrieved SOP evidence.\n"
        "• Visual extraction (Qwen2.5-VL) provides observations, not engineering facts.\n"
        "• OCR text may contain extraction errors, especially in low-quality scans.\n"
        "• Semantic retrieval is approximate; relevant passages may be missed.\n"
        "• This prototype uses sequential local model execution on Apple M4 (16 GB unified memory).\n"
        "• No cloud AI was used. Production deployment requires formal network/security hardening."
    ))

    # ── Final disclaimer (bottom) ─────────────────────────────────────────
    doc.add_paragraph()
    _add_warning_box(doc, "⚠  AI-DRAFTED — HUMAN REVIEW REQUIRED  ⚠")

    # ── Save ──────────────────────────────────────────────────────────────
    output_path = output_dir / f"Approval_Note_{ts}.docx"
    doc.save(str(output_path))
    return str(output_path)
