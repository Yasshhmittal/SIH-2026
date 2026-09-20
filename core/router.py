"""
core/router.py — Deterministic component selector.

The router is NOT another AI model; it is application-level logic that
decides which components to activate based on document characteristics.

Rules (from NEBULA plan §10):
  - If page is scanned/image → use PaddleOCR + Qwen2.5-VL
  - Reasoning model is always Qwen2.5-7B
  - Embedding model is always BGE-M3
  - OCR engine is always PaddleOCR
"""

from __future__ import annotations

import fitz  # PyMuPDF
from pathlib import Path


def needs_ocr(page: "fitz.Page") -> bool:
    """Return True if a PDF page has little/no selectable text (scanned)."""
    text = page.get_text("text").strip()
    # Heuristic: fewer than 20 chars of native text → treat as scanned
    return len(text) < 20


def needs_vision(page: "fitz.Page", ocr_text: str) -> bool:
    """
    Return True if the page likely contains meaningful visual content
    (diagrams, equipment photos, P&IDs) that benefits from VL analysis.

    Heuristic for prototype: page has images AND OCR text is short/incomplete.
    """
    image_list = page.get_images(full=False)
    return len(image_list) > 0 and len(ocr_text.strip()) < 500


def classify_document(pdf_path: str) -> dict:
    """
    Light-weight document classification.

    Returns a dict with:
      - page_count: int
      - has_native_text: bool  (any page with selectable text)
      - has_scanned_pages: bool
      - has_images: bool
      - task_class: str  ("Inspection Review" | "SOP" | "Unknown")
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    native_pages = 0
    scanned_pages = 0
    image_pages = 0

    for page in doc:
        text = page.get_text("text").strip()
        images = page.get_images(full=False)
        if len(text) >= 20:
            native_pages += 1
        else:
            scanned_pages += 1
        if images:
            image_pages += 1

    doc.close()

    # Simple task-class heuristic based on filename
    name_lower = path.stem.lower()
    if any(kw in name_lower for kw in ["sop", "procedure", "maint", "manual"]):
        task_class = "SOP"
    elif any(kw in name_lower for kw in ["report", "inspection", "audit", "check"]):
        task_class = "Inspection Review"
    else:
        task_class = "Unknown"

    return {
        "page_count": len(fitz.open(pdf_path)),
        "has_native_text": native_pages > 0,
        "has_scanned_pages": scanned_pages > 0,
        "has_images": image_pages > 0,
        "task_class": task_class,
    }


def build_component_plan(doc_info: dict) -> dict:
    """
    Given document classification, return the component plan.

    Always:
      - reasoning_model: "Qwen2.5-7B"
      - embedding_model:  "BGE-M3"
      - ocr_engine:       "PaddleOCR"

    Conditionally:
      - use_vision: True only if scanned pages or images detected
    """
    return {
        "reasoning_model": "Qwen2.5-7B",
        "embedding_model": "BGE-M3",
        "ocr_engine": "PaddleOCR",
        "use_ocr": doc_info.get("has_scanned_pages", True),
        "use_vision": doc_info.get("has_images", False) or doc_info.get("has_scanned_pages", False),
    }
