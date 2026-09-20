"""
document/loader.py — PDF extraction using PyMuPDF.

Flow (from plan §5.1):
  1. Open PDF with fitz (PyMuPDF).
  2. For each page: detect whether native text exists.
  3. If native text → extract directly.
  4. If scanned (little/no text) → render page image → PaddleOCR.
  5. Preserve document name, page number, source_type metadata.
  6. Save page image to cache/images/ for optional VL step.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

import fitz  # PyMuPDF

from core.schemas import PageRecord

NATIVE_TEXT_THRESHOLD = 20   # chars below this → treat page as scanned
IMAGE_DPI = 150               # render resolution for OCR (lower = faster on M4)
CACHE_DIR = Path(os.getenv("CACHE_DIR", "./cache"))


def load_pdf(pdf_path: str, run_ocr: bool = True) -> List[PageRecord]:
    """
    Load a PDF and return one PageRecord per page.

    Args:
        pdf_path:   Path to the PDF file.
        run_ocr:    If True, run PaddleOCR on scanned pages.
                    Set False for SOP pre-indexing if already cached.

    Returns:
        List of PageRecord (one per page).
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(path))
    doc_name = path.name
    image_dir = CACHE_DIR / "images" / path.stem
    image_dir.mkdir(parents=True, exist_ok=True)

    records: List[PageRecord] = []

    for page_num, page in enumerate(doc, start=1):
        native_text = page.get_text("text").strip()
        is_scanned = len(native_text) < NATIVE_TEXT_THRESHOLD

        image_path: str | None = None

        if is_scanned or run_ocr:
            # Render page to image for OCR / VL
            mat = fitz.Matrix(IMAGE_DPI / 72, IMAGE_DPI / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_file = image_dir / f"page_{page_num:04d}.png"
            pix.save(str(img_file))
            image_path = str(img_file)

        if is_scanned and run_ocr:
            # Delegate to PaddleOCR
            from document.ocr import run_ocr_on_page
            ocr_text, confidence = run_ocr_on_page(str(img_file))
            records.append(PageRecord(
                document=doc_name,
                page=page_num,
                text=ocr_text,
                source_type="ocr",
                ocr_confidence=confidence,
                image_path=image_path,
            ))
        else:
            records.append(PageRecord(
                document=doc_name,
                page=page_num,
                text=native_text,
                source_type="native",
                image_path=image_path,
            ))

    doc.close()
    return records
