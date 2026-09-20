"""
document/ocr.py — PaddleOCR wrapper for NEBULA.

Responsibilities (from plan §4.4):
  - Extract text from scanned page images
  - Return recognized text + per-page confidence
  - Does NOT reason over the document

PaddleOCR 3.7.0 API: uses .predict() instead of .ocr()
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

_ocr_engine = None   # module-level singleton to avoid repeated init overhead


def _get_engine():
    """Lazy-init PaddleOCR (CPU inference)."""
    global _ocr_engine
    if _ocr_engine is None:
        # Suppress noisy paddle logging
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(lang="en")
    return _ocr_engine


def run_ocr_on_page(image_path: str) -> Tuple[str, float]:
    """
    Run PaddleOCR on a single page image.

    Args:
        image_path: Absolute path to a rendered page PNG/JPG.

    Returns:
        (extracted_text, average_confidence)
        confidence is 0.0 if no text detected.
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found for OCR: {image_path}")

    engine = _get_engine()

    # PaddleOCR 3.7.0 uses .predict()
    result = engine.predict(image_path)

    if not result:
        return "", 0.0

    lines: list[str] = []
    confidences: list[float] = []

    # PaddleOCR 3.7 returns a list of result dicts
    # Each result dict has 'rec_texts' and 'rec_scores' keys
    for page_result in result:
        # Handle dict-style result (PaddleOCR 3.7+)
        if isinstance(page_result, dict):
            texts = page_result.get("rec_texts", page_result.get("rec_text", []))
            scores = page_result.get("rec_scores", page_result.get("rec_score", []))

            if isinstance(texts, str):
                texts = [texts]
            if isinstance(scores, (int, float)):
                scores = [scores]

            for text, score in zip(texts, scores):
                if text.strip():
                    lines.append(text.strip())
                    confidences.append(float(score))

        # Handle object-style result (some PaddleOCR versions return objects)
        elif hasattr(page_result, "rec_texts"):
            for text, score in zip(page_result.rec_texts, page_result.rec_scores):
                if text.strip():
                    lines.append(text.strip())
                    confidences.append(float(score))

        # Handle legacy list-of-lists format [[bbox, (text, conf)], ...]
        elif isinstance(page_result, list):
            for line in page_result:
                if line and len(line) >= 2:
                    text_conf = line[1]
                    if isinstance(text_conf, (list, tuple)) and len(text_conf) >= 2:
                        lines.append(str(text_conf[0]))
                        confidences.append(float(text_conf[1]))

    full_text = "\n".join(lines)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return full_text, round(avg_confidence, 4)
