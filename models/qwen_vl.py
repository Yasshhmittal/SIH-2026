"""
models/qwen_vl.py — Qwen2.5-VL-7B-Instruct wrapper for NEBULA (Ollama backend).

Responsibilities (from plan §4.2):
  - Visual understanding of scanned/image pages
  - Equipment photo interpretation
  - Structured JSON observation output

Called ONLY when the router detects image/scanned content.
Uses Ollama API at localhost:11434 — fully local, no cloud.
"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import List

import ollama

from core.schemas import PageRecord, VisualObservation

MODEL_NAME = os.getenv("QWEN_VL_MODEL", "qwen2.5vl:7b")
MAX_TOKENS = 512
# VL is the slowest, most memory-sensitive component — allow extra headroom.
VL_TIMEOUT = float(os.getenv("OLLAMA_VL_TIMEOUT", "360"))


def _client() -> "ollama.Client":
    """Ollama client with an explicit timeout (fully local, no cloud)."""
    return ollama.Client(timeout=VL_TIMEOUT)


VL_SYSTEM_PROMPT = """You are a precise industrial vision AI assistant.
Analyze the provided page image and extract only observable facts.
Do not invent information not visible in the image.
Respond only with valid JSON."""


class QwenVL:
    """Qwen2.5-VL-7B wrapper using Ollama API."""

    def unload(self) -> None:
        """Explicitly unload from Ollama to free memory."""
        try:
            _client().generate(model=MODEL_NAME, prompt='', keep_alive=0)
        except Exception:
            pass

    def analyze_page(self, page: PageRecord) -> List[VisualObservation]:
        """
        Run VL inference on a single page image via Ollama.
        Returns a list of VisualObservation objects.
        """
        if not page.image_path or not Path(page.image_path).exists():
            return []

        # Resize image to save memory (plan §12 recommendation)
        from PIL import Image
        import tempfile

        img = Image.open(page.image_path).convert("RGB")
        img.thumbnail((1024, 1024))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f.name)
            resized_path = f.name

        user_prompt = f"""Analyze this industrial document page image (page {page.page}).
List only what is directly observable.
Respond with JSON:
{{
  "observations": [
    {{"text": "...", "page": {page.page}, "confidence": "high|medium|low"}}
  ]
}}
If nothing significant is visible, return {{"observations": []}}."""

        try:
            response = _client().chat(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": VL_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": user_prompt,
                        "images": [resized_path],
                    },
                ],
                options={
                    "temperature": 0.0,
                    "num_predict": MAX_TOKENS,
                },
            )
            raw = response["message"]["content"].strip()
        except Exception as e:
            print(f"[QwenVL] Error: {e}")
            return []
        finally:
            # Clean up temp file
            try:
                os.unlink(resized_path)
            except Exception:
                pass

        # Parse JSON response
        try:
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
            data = json.loads(clean)
            observations = [
                VisualObservation(
                    text=obs.get("text", ""),
                    page=obs.get("page", page.page),
                    confidence=obs.get("confidence", "medium"),
                )
                for obs in data.get("observations", [])
            ]
            return observations
        except (json.JSONDecodeError, KeyError):
            # Return raw as single low-confidence observation
            if raw:
                return [VisualObservation(text=raw[:500], page=page.page, confidence="low")]
            return []
