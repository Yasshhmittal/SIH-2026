"""
scripts/generate_transformer_pdfs.py

Creates a new synthetic Inspection Report and SOP for an Electrical Transformer.
Saves them to data/inspection/ and data/knowledge/ respectively.
"""

import os
from pathlib import Path
import fitz  # PyMuPDF

def generate_transformer_docs():
    data_dir = Path("data")
    inspection_dir = data_dir / "inspection"
    knowledge_dir = data_dir / "knowledge"
    inspection_dir.mkdir(parents=True, exist_ok=True)
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    # 1. Inspection Report
    inspection_path = str(inspection_dir / "transformer_inspection.pdf")
    doc = fitz.open()

    # Cover
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), "SUBSTATION INSPECTION REPORT", fontsize=22, fontname="helv")
    page.insert_text((50, 120), "Equipment: 132/33kV Power Transformer TR-502", fontsize=14)
    page.insert_text((50, 150), "Location: Main Substation B", fontsize=12)
    page.insert_text((50, 180), "Date: 2026-10-05", fontsize=12)
    page.insert_text((50, 210), "Inspector: A. Kumar (Electrical Division)", fontsize=12)

    # Findings
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 60), "INSPECTION FINDINGS", fontsize=18, fontname="helv")
    findings = [
        "1. PHYSICAL INSPECTION",
        "   - Minor oil seepage observed near the bottom radiator valve.",
        "   - Cooling fans operate normally in manual mode.",
        "   - Silica gel breather color: Dark Green.",
        "   - Main tank oil level: 65% (Normal).",
        "",
        "2. TEMPERATURE METRICS",
        "   - Top Oil Temperature (TOT): 78°C.",
        "   - Winding Temperature Indicator (WTI): 82°C.",
        "   - Ambient temperature during inspection: 32°C.",
        "",
        "3. DISSOLVED GAS ANALYSIS (DGA) RESULTS",
        "   - Hydrogen (H2): 145 ppm (Elevated).",
        "   - Methane (CH4): 15 ppm.",
        "   - Ethylene (C2H4): 10 ppm.",
        "   - Acetylene (C2H2): 0 ppm.",
        "   - Carbon Monoxide (CO): 200 ppm.",
    ]
    y = 100
    for line in findings:
        page.insert_text((50, y), line, fontsize=11)
        y += 18

    doc.save(inspection_path)
    doc.close()
    print(f"✅ Created new Inspection Report: {inspection_path}")


    # 2. SOP Document
    sop_path = str(knowledge_dir / "SOP_ELEC_042_Transformer.pdf")
    doc = fitz.open()

    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), "STANDARD OPERATING PROCEDURE", fontsize=20, fontname="helv")
    page.insert_text((50, 120), "SOP-ELEC-042: Power Transformer Maintenance", fontsize=14)
    
    rules = [
        "1. TEMPERATURE LIMITS",
        "   - Normal Top Oil Temperature: < 75°C.",
        "   - Alert Top Oil Temperature: 75°C to 85°C. Action: Increase monitoring",
        "     frequency and verify cooling fan operation.",
        "   - Trip Top Oil Temperature: > 85°C. Action: Automatic trip / immediate shutdown.",
        "",
        "2. DISSOLVED GAS ANALYSIS (DGA)",
        "   - Hydrogen (H2) < 50 ppm: Normal operation.",
        "   - Hydrogen (H2) > 100 ppm: Indicates potential partial discharge or corona.",
        "     Action: Schedule an outage within 7 days for electrical testing.",
        "   - Acetylene (C2H2) > 5 ppm: Indicates active arcing. Action: Immediate",
        "     emergency shutdown required.",
        "",
        "3. SILICA GEL BREATHER",
        "   - Orange color indicates active moisture absorption (Good).",
        "   - Green or transparent color indicates moisture saturation.",
        "   - Action: Replace silica gel immediately when it turns green to prevent",
        "     moisture ingress into the transformer oil.",
        "",
        "4. OIL LEAKS",
        "   - Any observed oil seepage must be logged.",
        "   - Seepage without active dripping can be repaired during the next scheduled",
        "     maintenance window."
    ]
    y = 180
    for line in rules:
        page.insert_text((50, y), line, fontsize=11)
        y += 18

    doc.save(sop_path)
    doc.close()
    print(f"✅ Created new SOP: {sop_path}")

if __name__ == "__main__":
    generate_transformer_docs()
