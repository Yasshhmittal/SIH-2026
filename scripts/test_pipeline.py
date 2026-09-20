"""
scripts/test_pipeline.py — End-to-end integration test for NEBULA.

Creates synthetic test PDFs, then runs the full pipeline:
  Document loading → OCR → Chunking → Indexing → Retrieval → Reasoning → Validation → DOCX

Usage:
    python scripts/test_pipeline.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


# ── Create synthetic test documents ───────────────────────────────────────────

def create_test_pdfs() -> tuple[str, str]:
    """
    Create a synthetic inspection report and SOP using fitz (PyMuPDF).
    Returns (inspection_path, sop_path).
    """
    import fitz

    data_dir = Path("data")
    inspection_dir = data_dir / "inspection"
    knowledge_dir = data_dir / "knowledge"
    inspection_dir.mkdir(parents=True, exist_ok=True)
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    # ── Inspection Report ─────────────────────────────────────────────────
    inspection_path = str(inspection_dir / "inspection_report.pdf")
    doc = fitz.open()

    # Page 1: Cover page
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), "INSPECTION REPORT", fontsize=24, fontname="helv")
    page.insert_text((50, 120), "Equipment: Centrifugal Pump P-101", fontsize=14)
    page.insert_text((50, 150), "Location: Crude Distillation Unit (CDU)", fontsize=12)
    page.insert_text((50, 180), "Date: 2026-08-15", fontsize=12)
    page.insert_text((50, 210), "Inspector: R. Sharma (MRPL Inspection Division)", fontsize=12)
    page.insert_text((50, 250), "Report ID: MRPL-INS-2026-0847", fontsize=12)
    page.insert_text((50, 290), "Classification: CONFIDENTIAL — Internal Use Only", fontsize=11)

    # Page 2: Findings
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 60), "INSPECTION FINDINGS", fontsize=18, fontname="helv")

    findings = [
        "1. MECHANICAL SEAL INSPECTION",
        "   - Primary mechanical seal shows visible leakage on the atmospheric side.",
        "   - Leak rate estimated at 15-20 drops per minute.",
        "   - Seal face wear pattern indicates misalignment.",
        "   - Carbon face deposits observed on the seal surface.",
        "",
        "2. VIBRATION ANALYSIS",
        "   - Overall vibration measured at 12.4 mm/s RMS (alarm threshold: 7.1 mm/s).",
        "   - Dominant frequency at 1x running speed (2980 RPM) suggests imbalance.",
        "   - Sub-synchronous vibration at 0.43x detected, possible oil whirl.",
        "   - Bearing housing temperature: 92°C (normal: <75°C).",
        "",
        "3. CORROSION ASSESSMENT",
        "   - Pipe wall thickness at elbow: 4.2 mm (original: 8.0 mm).",
        "   - Corrosion rate: 0.38 mm/year.",
        "   - External surface pitting observed near flange connection.",
        "   - Coating degradation: 40% of surface area affected.",
        "",
        "4. SUMMARY",
        "   - Pump P-101 requires immediate maintenance attention.",
        "   - Seal replacement recommended within 48 hours.",
        "   - Vibration source to be investigated — suspect rotor imbalance or",
        "     bearing degradation.",
        "   - Pipe section at CDU-E-103 elbow approaching minimum retirement thickness.",
    ]
    y = 90
    for line in findings:
        page.insert_text((50, y), line, fontsize=10)
        y += 16

    # Page 3: Recommendations
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 60), "RECOMMENDATIONS & PRIORITY", fontsize=18, fontname="helv")

    recs = [
        "PRIORITY 1 (IMMEDIATE — within 48 hours):",
        "  - Replace mechanical seal on Pump P-101.",
        "  - Verify seal alignment using laser alignment tool.",
        "  - Flush seal chamber and inspect seal cavity for debris.",
        "",
        "PRIORITY 2 (URGENT — within 1 week):",
        "  - Perform detailed vibration spectrum analysis.",
        "  - Check rotor balance and bearing condition.",
        "  - Monitor bearing temperature continuously.",
        "",
        "PRIORITY 3 (SCHEDULED — within 1 month):",
        "  - Schedule pipe wall thickness survey for CDU-E-103 section.",
        "  - Plan external coating repair program.",
        "  - Update corrosion monitoring records.",
        "",
        "SAFETY NOTE:",
        "  This inspection report is provided for maintenance planning purposes.",
        "  All corrective actions must be reviewed and approved by the",
        "  designated authority before execution.",
        "  Equipment shall not be returned to service without proper clearance.",
    ]
    y = 90
    for line in recs:
        page.insert_text((50, y), line, fontsize=10)
        y += 16

    doc.save(inspection_path)
    doc.close()
    print(f"  ✅ Created: {inspection_path} (3 pages)")

    # ── SOP Document ──────────────────────────────────────────────────────
    sop_path = str(knowledge_dir / "SOP_MAINT_017.pdf")
    doc = fitz.open()

    # Page 1: SOP Cover
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), "STANDARD OPERATING PROCEDURE", fontsize=20, fontname="helv")
    page.insert_text((50, 120), "SOP-MAINT-017: Centrifugal Pump Maintenance", fontsize=14)
    page.insert_text((50, 150), "Revision: 4.2", fontsize=12)
    page.insert_text((50, 170), "Effective Date: 2025-01-15", fontsize=12)
    page.insert_text((50, 190), "Approved by: Chief Maintenance Engineer", fontsize=12)
    page.insert_text((50, 220), "Scope: All centrifugal pumps in CDU, VDU, and FCC units.", fontsize=11)
    page.insert_text((50, 260), "1. PURPOSE", fontsize=14, fontname="helv")
    purpose = [
        "This SOP establishes mandatory maintenance procedures for centrifugal",
        "pumps in refinery service, including inspection criteria, corrective",
        "action thresholds, and documentation requirements.",
    ]
    y = 285
    for line in purpose:
        page.insert_text((50, y), line, fontsize=10)
        y += 16

    # Page 2: Vibration criteria
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 60), "2. VIBRATION MONITORING CRITERIA", fontsize=14, fontname="helv")

    vib = [
        "2.1 All centrifugal pumps shall be monitored per ISO 10816-7.",
        "",
        "2.2 Vibration severity thresholds for pumps rated above 15 kW:",
        "    Zone A (Good):       < 3.5 mm/s RMS",
        "    Zone B (Acceptable): 3.5 - 7.1 mm/s RMS",
        "    Zone C (Alert):      7.1 - 11.0 mm/s RMS — Plan corrective action",
        "    Zone D (Danger):     > 11.0 mm/s RMS — STOP IMMEDIATELY, mandatory",
        "                         inspection before restart.",
        "",
        "2.3 When vibration exceeds Zone C threshold (7.1 mm/s):",
        "    a) Notify shift supervisor within 1 hour.",
        "    b) Initiate root cause analysis.",
        "    c) Schedule corrective maintenance within 1 week.",
        "",
        "2.4 When vibration exceeds Zone D threshold (11.0 mm/s):",
        "    a) STOP pump immediately (emergency shutdown if necessary).",
        "    b) Notify plant manager and safety department.",
        "    c) Do not restart without documented inspection and clearance.",
        "    d) Perform comprehensive vibration spectrum analysis.",
        "    e) Check bearing condition, rotor balance, and coupling alignment.",
        "",
        "2.5 Sub-synchronous vibration below 0.5x running speed indicates",
        "    potential oil whirl/whip in journal bearings. This requires",
        "    immediate investigation of bearing oil supply and clearances.",
    ]
    y = 90
    for line in vib:
        page.insert_text((50, y), line, fontsize=10)
        y += 16

    # Page 3: Seal maintenance
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 60), "3. MECHANICAL SEAL MAINTENANCE", fontsize=14, fontname="helv")

    seal = [
        "3.1 Mechanical seal inspection shall be performed:",
        "    a) During every pump overhaul.",
        "    b) When visible leakage exceeds 10 drops per minute.",
        "    c) When process fluid contamination is suspected.",
        "",
        "3.2 Seal replacement criteria:",
        "    a) Visible leakage rate > 10 drops/min → REPLACE within 48 hours.",
        "    b) Seal face scoring or chipping → REPLACE immediately.",
        "    c) Carbon ring wear > 2mm → REPLACE during next shutdown.",
        "",
        "3.3 Seal replacement procedure:",
        "    Step 1: Isolate pump (LOTO per SOP-SAFE-003).",
        "    Step 2: Drain and flush seal chamber.",
        "    Step 3: Remove old seal assembly.",
        "    Step 4: Inspect shaft and seal cavity for damage.",
        "    Step 5: Verify shaft runout < 0.05 mm.",
        "    Step 6: Install new seal per manufacturer specifications.",
        "    Step 7: Verify seal alignment using laser alignment tool.",
        "    Step 8: Pressure test seal chamber.",
        "    Step 9: Document all measurements in maintenance record.",
        "",
        "3.4 Seal misalignment indicators:",
        "    - Uneven wear pattern on seal face.",
        "    - Carbon deposits on atmospheric side.",
        "    - Excessive leakage with new seal installed.",
    ]
    y = 90
    for line in seal:
        page.insert_text((50, y), line, fontsize=10)
        y += 16

    # Page 4: Corrosion monitoring
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 60), "4. PIPE WALL THICKNESS & CORROSION", fontsize=14, fontname="helv")

    corr = [
        "4.1 Minimum wall thickness requirements:",
        "    a) All piping shall maintain thickness above the calculated",
        "       minimum retirement thickness per API 570.",
        "    b) For carbon steel pipes in hydrocarbon service:",
        "       Minimum retirement thickness = design thickness - corrosion allowance.",
        "",
        "4.2 Corrosion monitoring frequency:",
        "    a) Corrosion rate < 0.1 mm/year: inspect every 5 years.",
        "    b) Corrosion rate 0.1 - 0.25 mm/year: inspect every 2 years.",
        "    c) Corrosion rate 0.25 - 0.5 mm/year: inspect annually.",
        "    d) Corrosion rate > 0.5 mm/year: inspect every 6 months,",
        "       plan replacement.",
        "",
        "4.3 When measured thickness reaches retirement threshold:",
        "    a) Remove pipe section from service.",
        "    b) Replace with approved material specification.",
        "    c) Investigate root cause of accelerated corrosion.",
        "",
        "4.4 External corrosion under insulation (CUI):",
        "    a) Inspect all insulated piping operating between 50-175°C.",
        "    b) Remove insulation at suspected locations for visual inspection.",
        "    c) Apply approved coating system after repair.",
        "",
        "4.5 Corrosion rate calculation:",
        "    Rate = (Original thickness - Measured thickness) / Service years.",
        "    Record all measurements in the corrosion monitoring database.",
    ]
    y = 90
    for line in corr:
        page.insert_text((50, y), line, fontsize=10)
        y += 16

    # Page 5: Bearing temperature
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 60), "5. BEARING TEMPERATURE MONITORING", fontsize=14, fontname="helv")

    bearing = [
        "5.1 Bearing housing temperature limits:",
        "    a) Normal operating range: < 75°C.",
        "    b) Alert level: 75-90°C — investigate cause.",
        "    c) Alarm level: 90-100°C — plan immediate shutdown.",
        "    d) Trip level: > 100°C — automatic or manual emergency shutdown.",
        "",
        "5.2 When bearing temperature exceeds alert level (75°C):",
        "    a) Check lubrication oil level and quality.",
        "    b) Verify cooling water supply to bearing housing.",
        "    c) Check for abnormal vibration simultaneously.",
        "    d) Document findings and report to maintenance supervisor.",
        "",
        "5.3 When bearing temperature exceeds alarm level (90°C):",
        "    a) Prepare for controlled shutdown.",
        "    b) Notify operations and safety.",
        "    c) Switch to standby pump if available.",
        "    d) Do NOT restart until bearing has been inspected.",
        "",
        "5.4 Combined high vibration and high bearing temperature indicates",
        "    potential bearing failure. This combination requires IMMEDIATE",
        "    shutdown regardless of individual threshold levels.",
    ]
    y = 90
    for line in bearing:
        page.insert_text((50, y), line, fontsize=10)
        y += 16

    doc.save(sop_path)
    doc.close()
    print(f"  ✅ Created: {sop_path} (5 pages)")

    return inspection_path, sop_path


# ── Phase 1 Test: Document + OCR + Chunking ───────────────────────────────────

def test_phase1(inspection_path: str, sop_path: str):
    """Test document loading, OCR, and chunking."""
    from document.loader import load_pdf
    from document.chunker import chunk_document

    print("\n── Phase 1: Document Loading + OCR + Chunking ──")

    # Load inspection report
    t0 = time.time()
    pages = load_pdf(inspection_path, run_ocr=True)
    elapsed = time.time() - t0
    print(f"  Inspection: {len(pages)} pages loaded in {elapsed:.1f}s")
    for p in pages:
        src = f"[{p.source_type}]"
        conf = f" conf={p.ocr_confidence:.2f}" if p.ocr_confidence else ""
        img = " 📷" if p.image_path else ""
        print(f"    Page {p.page} {src}{conf}{img} — {len(p.text)} chars")

    # Load SOP
    t0 = time.time()
    sop_pages = load_pdf(sop_path, run_ocr=True)
    elapsed = time.time() - t0
    print(f"  SOP: {len(sop_pages)} pages loaded in {elapsed:.1f}s")

    # Chunk both
    insp_chunks = chunk_document(pages)
    sop_chunks = chunk_document(sop_pages)
    print(f"  Inspection chunks: {len(insp_chunks)}")
    print(f"  SOP chunks: {len(sop_chunks)}")

    for c in sop_chunks[:3]:
        print(f"    {c.chunk_id}: {c.document} p.{c.page} — {len(c.text)} chars")

    return pages, sop_pages, sop_chunks


# ── Phase 2 Test: BGE-M3 Indexing + Retrieval ─────────────────────────────────

def test_phase2(sop_chunks, sop_path, pages):
    """Test embedding index and cosine retrieval."""
    from rag.index import build_or_load_index
    from rag.retrieve import retrieve_top_k
    from models.bge import BGE

    print("\n── Phase 2: BGE-M3 Indexing + Retrieval ──")

    # Build index
    t0 = time.time()
    embedding_matrix, chunk_list = build_or_load_index(sop_chunks, sop_path)
    elapsed = time.time() - t0
    print(f"  Index: {embedding_matrix.shape} in {elapsed:.1f}s")

    # Retrieve for a test query
    query = "seal leakage on pump P-101, vibration exceeds threshold"
    bge = BGE()
    t0 = time.time()
    retrieved = retrieve_top_k(query, embedding_matrix, chunk_list, bge, k=3)
    elapsed = time.time() - t0
    bge.unload()

    print(f"  Retrieval ({elapsed:.1f}s):")
    for rc in retrieved:
        print(f"    {rc.chunk.document} p.{rc.chunk.page} | score={rc.score:.3f} | {rc.chunk.text[:80]}…")

    return embedding_matrix, chunk_list, retrieved


# ── Phase 3+: Full Agent Pipeline ─────────────────────────────────────────────

def test_full_agent(inspection_path, sop_path):
    """Run the complete agent pipeline end-to-end."""
    from core.agent import run_agent

    print("\n── Full Agent Pipeline ──")

    task = (
        "Analyze this inspection report against the maintenance SOP. "
        "Identify supported findings, cite the evidence, state uncertainty, "
        "and prepare a human-reviewable draft approval note."
    )

    t0 = time.time()
    state = run_agent(
        task=task,
        inspection_path=inspection_path,
        sop_path=sop_path,
        progress_callback=lambda msg: print(f"  {msg}"),
    )
    elapsed = time.time() - t0

    print(f"\n  Total pipeline time: {elapsed:.1f}s")
    print(f"  Pages: {len(state.pages)}")
    print(f"  Chunks indexed: {len(state.chunks)}")
    print(f"  Retrieved: {len(state.retrieved)}")

    if state.reasoning:
        r = state.reasoning
        print(f"  Supported findings: {len(r.supported_findings)}")
        print(f"  Inferences: {len(r.inferences)}")
        print(f"  Uncertainties: {len(r.uncertainties)}")
        print(f"  Recommended action: {r.recommended_action[:100]}…")

    if state.validation:
        v = state.validation
        print(f"  Validation passed: {v.passed}")
        if v.failure_reason:
            print(f"  Failure reason: {v.failure_reason}")

    if state.docx_path:
        print(f"  ✅ DOCX: {state.docx_path}")
    else:
        print(f"  ❌ No DOCX generated")

    return state


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n🛡️  NEBULA — End-to-End Integration Test")
    print("=" * 60)

    # Create test documents
    print("\n── Creating synthetic test PDFs ──")
    inspection_path, sop_path = create_test_pdfs()

    # Phase 1: Document + OCR + Chunking
    pages, sop_pages, sop_chunks = test_phase1(inspection_path, sop_path)

    # Phase 2: Indexing + Retrieval
    embedding_matrix, chunk_list, retrieved = test_phase2(sop_chunks, sop_path, pages)

    # Full Agent Pipeline (Phase 3-8)
    state = test_full_agent(inspection_path, sop_path)

    # Final summary
    print("\n" + "=" * 60)
    print("  INTEGRATION TEST SUMMARY")
    print("=" * 60)
    checks = {
        "PDFs created":           True,
        "Pages loaded":           len(pages) > 0,
        "SOP chunked":            len(sop_chunks) > 0,
        "Index built":            embedding_matrix is not None,
        "Retrieval works":        len(retrieved) > 0,
        "Reasoning ran":          state.reasoning is not None,
        "Validation ran":         state.validation is not None,
        "DOCX generated":         state.docx_path is not None,
    }
    all_pass = True
    for name, ok in checks.items():
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
        if not ok:
            all_pass = False

    if all_pass:
        print("\n  🎉 Full pipeline working end-to-end!\n")
    else:
        print("\n  ⚠️  Some steps need attention.\n")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
