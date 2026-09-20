"""
scripts/preindex.py — Pre-build SOP embedding cache.

Run once before launching the UI:
    python scripts/preindex.py --sop data/knowledge/SOP_MAINT_017.pdf

This saves BGE-M3 embeddings to cache/ so the first agent run is faster.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-index SOP for NEBULA RAG")
    parser.add_argument(
        "--sop",
        default="data/knowledge/SOP_MAINT_017.pdf",
        help="Path to SOP PDF (default: data/knowledge/SOP_MAINT_017.pdf)",
    )
    args = parser.parse_args()

    sop_path = Path(args.sop)
    if not sop_path.exists():
        print(f"❌ SOP file not found: {sop_path}")
        print("   Place your SOP PDF in data/knowledge/ or pass --sop <path>")
        sys.exit(1)

    print(f"🛡️  NEBULA Pre-indexer")
    print(f"   SOP: {sop_path}")

    from document.loader import load_pdf
    from document.chunker import chunk_document
    from rag.index import build_or_load_index

    print("📄 Loading and chunking SOP...")
    pages = load_pdf(str(sop_path), run_ocr=True)
    chunks = chunk_document(pages)
    print(f"   Pages: {len(pages)} | Chunks: {len(chunks)}")

    print("🔢 Computing BGE-M3 embeddings (this takes ~1–3 min first time)...")
    embeddings, chunk_list = build_or_load_index(chunks, str(sop_path))

    print(f"\n✅ Index ready: {len(chunk_list)} chunks | Embedding shape: {embeddings.shape}")
    print("   Cache saved to ./cache/")
    print("   You can now run: streamlit run app.py\n")


if __name__ == "__main__":
    main()
