"""
scripts/smoke_test.py — Phase-0 component verification (Ollama backend).

Tests each required component independently BEFORE UI work begins.
Run this script first. Do not proceed if any component fails.

Usage:
    python scripts/smoke_test.py [--skip-vl] [--skip-ocr]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _ok(msg: str) -> None:
    print(f"  ✅  {msg}")


def _fail(msg: str) -> None:
    print(f"  ❌  {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠️   {msg}")


# ── Test 0: Ollama connectivity ───────────────────────────────────────────────

def test_ollama() -> bool:
    _header("Test 0 — Ollama connectivity")
    try:
        import ollama
        models = ollama.list()
        model_names = [m.model for m in models.models]
        _ok(f"Ollama connected. Models available: {model_names}")

        required = {"qwen2.5:7b", "qwen2.5vl:7b", "bge-m3:latest"}
        found = set()
        for name in model_names:
            for req in required:
                if req in name:
                    found.add(req)
        missing = required - found
        if missing:
            _fail(f"Missing models: {missing}")
            return False
        _ok("All 3 Ollama models present ✓")
        return True
    except Exception as e:
        _fail(f"Ollama connection failed: {e}")
        _warn("Is 'ollama serve' running?")
        return False


# ── Test 1: Qwen2.5-7B ────────────────────────────────────────────────────────

def test_qwen_text() -> bool:
    _header("Test 1 — Qwen2.5-7B (text → response)")
    try:
        from models.qwen_text import QwenText
        from core.schemas import PageRecord, RetrievedChunk, Chunk

        t0 = time.time()
        qwen = QwenText()

        dummy_pages = [PageRecord(
            document="test.pdf", page=1,
            text="Pump P-101 shows elevated vibration at 12 Hz.",
            source_type="native",
        )]
        dummy_chunks = [Chunk(
            chunk_id="sop_p0001_c000", document="SOP.pdf", page=1,
            text="Elevated vibration above 10 Hz requires immediate inspection per SOP-MAINT-017 section 4.3.",
        )]
        dummy_retrieved = [RetrievedChunk(chunk=dummy_chunks[0], score=0.82)]

        result = qwen.reason(
            task="Does the vibration level require action?",
            pages=dummy_pages,
            retrieved=dummy_retrieved,
        )
        elapsed = time.time() - t0
        _ok(f"Qwen2.5-7B responded in {elapsed:.1f}s")
        _ok(f"Task class: {result.task_class}")
        _ok(f"Supported findings: {len(result.supported_findings)}")
        _ok(f"Raw JSON length: {len(result.raw_json or '')} chars")
        return True
    except Exception as e:
        _fail(f"Qwen2.5-7B failed: {e}")
        return False


# ── Test 2: BGE-M3 ────────────────────────────────────────────────────────────

def test_bge() -> bool:
    _header("Test 2 — BGE-M3 (text → embedding vector)")
    try:
        from models.bge import BGE
        t0 = time.time()
        bge = BGE()
        vecs = bge.encode(["seal leakage on pump P-101", "elevated vibration detected"])
        elapsed = time.time() - t0
        _ok(f"BGE-M3 responded in {elapsed:.1f}s")
        _ok(f"Embedding shape: {vecs.shape}  (expected: (2, 1024))")
        assert vecs.shape[0] == 2, "Expected 2 embeddings"
        assert vecs.shape[1] > 100, "Embedding dimension too small"
        return True
    except Exception as e:
        _fail(f"BGE-M3 failed: {e}")
        return False


# ── Test 3: PaddleOCR ─────────────────────────────────────────────────────────

def test_paddleocr() -> bool:
    _header("Test 3 — PaddleOCR (image → text)")
    try:
        from PIL import Image, ImageDraw
        import tempfile

        # Create a synthetic text image
        img = Image.new("RGB", (600, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "PUMP P-101 VIBRATION LEVEL: 12 Hz EXCEEDED", fill=(0, 0, 0))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f.name)
            test_img = f.name

        from document.ocr import run_ocr_on_page
        t0 = time.time()
        text, confidence = run_ocr_on_page(test_img)
        elapsed = time.time() - t0

        _ok(f"PaddleOCR responded in {elapsed:.1f}s")
        _ok(f"Extracted text: '{text[:80]}'")
        _ok(f"Confidence: {confidence:.3f}")
        return True
    except Exception as e:
        _fail(f"PaddleOCR failed: {e}")
        return False


# ── Test 4: Qwen2.5-VL-7B ────────────────────────────────────────────────────

def test_qwen_vl() -> bool:
    _header("Test 4 — Qwen2.5-VL-7B (image → observations)")
    try:
        from PIL import Image, ImageDraw
        import tempfile

        # Create a minimal test image with some text
        img = Image.new("RGB", (400, 300), color=(200, 210, 220))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Industrial Equipment Inspection", fill=(0, 0, 0))
        draw.text((10, 40), "Pump P-101 — Visual check", fill=(0, 0, 0))
        draw.rectangle([50, 100, 350, 250], outline=(255, 0, 0), width=3)
        draw.text((80, 140), "CORROSION NOTED", fill=(200, 0, 0))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f.name)
            test_img = f.name

        from core.schemas import PageRecord
        from models.qwen_vl import QwenVL

        page = PageRecord(
            document="test.pdf", page=1,
            text="", source_type="ocr",
            image_path=test_img,
        )

        t0 = time.time()
        vl = QwenVL()
        obs = vl.analyze_page(page)
        elapsed = time.time() - t0

        _ok(f"Qwen2.5-VL-7B responded in {elapsed:.1f}s")
        _ok(f"Observations returned: {len(obs)}")
        for o in obs[:3]:
            _ok(f"  → [{o.confidence}] {o.text[:80]}")
        return True
    except Exception as e:
        _fail(f"Qwen2.5-VL-7B failed: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="NEBULA smoke tests (Ollama)")
    parser.add_argument("--skip-vl", action="store_true", help="Skip Qwen2.5-VL test (slowest)")
    parser.add_argument("--skip-ocr", action="store_true", help="Skip PaddleOCR test")
    args = parser.parse_args()

    print("\n🛡️  NEBULA Phase-0 Smoke Tests (Ollama backend)")
    print("   Testing all required components before implementation.\n")

    results = {}

    results["ollama"]  = test_ollama()
    if not results["ollama"]:
        print("\n  ⛔ Ollama not reachable. Cannot proceed.")
        sys.exit(1)

    results["qwen7b"]  = test_qwen_text()
    results["bge"]     = test_bge()

    if not args.skip_ocr:
        results["paddle"] = test_paddleocr()
    else:
        _warn("PaddleOCR test skipped (--skip-ocr)")

    if not args.skip_vl:
        results["qwenvl"] = test_qwen_vl()
    else:
        _warn("Qwen2.5-VL test skipped (--skip-vl)")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    all_pass = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {name}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n  🎉 All components verified. Ready to proceed.\n")
        sys.exit(0)
    else:
        print("\n  ⛔ Some components failed. Fix before proceeding.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
