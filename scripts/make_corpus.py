"""Generate a synthetic MRPL-style demo corpus.

Real refinery documents are confidential, so the demo corpus is written from
public standards practice (API 570 / 510 shapes) with invented tag numbers and
readings. Every file is marked SYNTHETIC in its header so nothing here can be
mistaken for MRPL data.

    python scripts/make_corpus.py            # write files and index them
    python scripts/make_corpus.py --no-index # just write the files
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "orgs" / "mrpl" / "kb_source"

SOP_INSPECTION = """SYNTHETIC DEMO DOCUMENT — not real MRPL data

SOP-INS-07
PIPING INSPECTION AND THICKNESS EVALUATION

1. Purpose
This procedure governs ultrasonic thickness survey, evaluation and disposition
of process piping within the refinery battery limits.

2. Scope
Applies to all carbon steel and low-alloy piping in hydrocarbon and sour
service, nominal bore 2 inch and above.

3. Definitions
3.1 Nominal thickness is the as-built wall thickness recorded on the isometric.
3.2 Measured thickness is the minimum reading obtained at a condition
    monitoring location during ultrasonic survey.
3.3 Retirement thickness is the minimum wall thickness below which a component
    must be repaired, derated or replaced.

4. Retirement Thickness Criteria
4.1 Retirement thickness shall be established from the design pressure, the
    material allowable stress and a corrosion allowance, and shall be recorded
    on the circuit datasheet.
4.2 In the absence of a circuit-specific value, the minimum retirement
    thickness for 8 inch carbon steel piping in sour service shall be 6.4 mm.
    Components measuring below this value shall be derated or replaced.
4.3 For 6 inch carbon steel piping in sour service the minimum retirement
    thickness shall be 5.6 mm.
4.4 For 12 inch carbon steel piping in wet hydrocarbon service the minimum
    retirement thickness shall be 7.1 mm.

5. Inspection Intervals
5.1 Re-inspection shall occur at one half of calculated remaining life, or five
    years, whichever is the lesser.
5.2 Where the calculated corrosion rate exceeds 0.25 mm per year the circuit
    shall be reclassified as high consequence and the interval shortened to
    one half of remaining life or three years, whichever is the lesser.
5.3 Circuits with a corrosion rate below 0.05 mm per year may be extended to a
    ten year interval subject to approval by the Chief Inspector.

6. Corrosion Rate Calculation
6.1 The long-term corrosion rate shall be calculated as the difference between
    nominal and measured thickness divided by the years in service.
6.2 Remaining life shall be calculated as the difference between measured and
    retirement thickness divided by the corrosion rate.
6.3 Where measured thickness is already at or below retirement thickness, no
    remaining life exists and the component shall be treated as a present
    deficiency requiring immediate disposition.

7. Disposition and Approval
7.1 A component below retirement thickness shall be reported to the Inspection
    Engineer within one working day.
7.2 Derating, repair or replacement shall be raised as a work order under
    Management of Change.
7.3 An approval note shall record the findings, the calculation with steps, the
    governing clause of this procedure, and the recommended disposition.
7.4 Approval authority for derating rests with the Chief Inspector. Replacement
    exceeding fifty lakh rupees requires Head of Department endorsement.
"""

SOP_MOC = """SYNTHETIC DEMO DOCUMENT — not real MRPL data

SOP-ENG-12
MANAGEMENT OF CHANGE

1. Purpose
To ensure that changes to process, equipment or operating envelope are assessed
for risk and formally authorised before implementation.

2. When MOC Is Required
2.1 Any change to design pressure, design temperature or material of
    construction.
2.2 Replacement of a component with one of differing specification.
2.3 Derating of equipment below its original design conditions.
2.4 Temporary repairs intended to remain in service beyond ninety days.

3. Exclusions
3.1 Replacement in kind, being a component identical in specification to the
    one removed, does not require MOC.
3.2 Routine maintenance carried out under an approved procedure is excluded.

4. Approval Matrix
4.1 Changes with no safety or environmental consequence: Area Engineer.
4.2 Changes affecting a pressure envelope: Chief Inspector and Area Manager.
4.3 Changes affecting a safety instrumented function: Chief Inspector, Area
    Manager and Head of Safety.
4.4 Derating of a pressure system: Chief Inspector, with notification to the
    statutory authority where required.

5. Documentation
5.1 Each MOC shall record the technical basis, the risk assessment, the
    approvals obtained and the close-out verification.
5.2 MOC records shall be retained for the life of the asset plus seven years.
"""

VESSEL_STANDARD = """SYNTHETIC DEMO DOCUMENT — not real MRPL data

SOP-INS-11
PRESSURE VESSEL INSPECTION

1. Scope
Applies to unfired pressure vessels, including columns, drums and heat
exchanger shells, within refinery battery limits.

2. External Inspection
2.1 External visual inspection shall be carried out at intervals not exceeding
    five years.
2.2 Insulation shall be removed at suspect locations to inspect for corrosion
    under insulation where the operating temperature lies between minus four
    and one hundred and seventy five degrees Celsius.

3. Internal Inspection
3.1 Internal inspection interval shall not exceed one half of remaining life or
    ten years, whichever is the lesser.
3.2 Where internal inspection is impractical, an on-stream inspection plan
    using ultrasonic and radiographic methods may be substituted with the
    approval of the Chief Inspector.

4. Thickness Criteria
4.1 The minimum retirement thickness for a vessel shell shall be calculated
    from the design code and recorded on the vessel datasheet.
4.2 Localised thinning over an area smaller than the lesser of one third of the
    vessel diameter or five hundred millimetres may be evaluated by local
    averaging in accordance with the design code.

5. Reporting
5.1 An inspection report shall record all condition monitoring location
    readings, the calculated corrosion rates and the next inspection due date.
"""

INSPECTION_REPORT = """SYNTHETIC DEMO DOCUMENT — not real MRPL data

ULTRASONIC THICKNESS SURVEY REPORT
Report number: INS-2026-0418
Unit: Crude Distillation Unit (CDU)
Circuit: 8-P-1204, overhead vapour line to condenser
Service: Sour hydrocarbon, wet
Material: ASTM A106 Grade B carbon steel
Nominal bore: 8 inch
Nominal wall thickness: 8.0 mm
Years in service: 7
Survey date: 2026-08-28
Inspector: (synthetic record)

CONDITION MONITORING LOCATION READINGS

CML | Location | Nominal mm | Measured mm | Retirement mm | Status
CML-01 | Straight run upstream | 8.0 | 7.4 | 6.4 | acceptable
CML-02 | Elbow E-12 extrados | 8.0 | 7.1 | 6.4 | acceptable
CML-03 | Elbow E-14 extrados | 8.0 | 5.9 | 6.4 | BELOW RETIREMENT
CML-04 | Tee T-03 branch | 8.0 | 6.8 | 6.4 | monitor
CML-05 | Straight run downstream | 8.0 | 7.3 | 6.4 | acceptable
CML-06 | Reducer R-02 | 8.0 | 6.6 | 6.4 | monitor

OBSERVATIONS
The lowest reading in the circuit is 5.9 mm at CML-03, Elbow E-14 extrados,
which is below the retirement thickness of 6.4 mm stated for 8 inch carbon
steel piping in sour service. Wall loss is concentrated on the extrados of the
elbow, consistent with erosion-corrosion at a change of direction.

CML-04 and CML-06 are above retirement thickness but show higher than average
loss and should be added to the next survey scope.

No external corrosion, coating breakdown or insulation damage was observed on
the circuit during the accompanying external visual inspection.

RECOMMENDATIONS
1. Report the CML-03 deficiency to the Inspection Engineer.
2. Evaluate derating or replacement of the Elbow E-14 spool.
3. Raise the disposition under Management of Change.
4. Shorten the survey interval for this circuit pending disposition.
"""

CORRESPONDENCE = """SYNTHETIC DEMO DOCUMENT — not real MRPL data

INTERNAL MEMORANDUM

From: Inspection Engineer, CDU
To: Chief Inspector
Date: 2026-08-30
Subject: Thickness deficiency, circuit 8-P-1204, Elbow E-14

Further to ultrasonic survey report INS-2026-0418 dated 28 August 2026, the
lowest reading on circuit 8-P-1204 is 5.9 mm at CML-03, Elbow E-14 extrados,
against a retirement thickness of 6.4 mm per SOP-INS-07 clause 4.2.

The circuit has been in service seven years against a nominal wall of 8.0 mm,
giving a long-term corrosion rate of approximately 0.3 mm per year. As the
measured thickness is already below retirement thickness, clause 6.3 applies
and no remaining life may be claimed.

Since the calculated corrosion rate exceeds 0.25 mm per year, clause 5.2
requires the circuit to be reclassified as high consequence.

I recommend replacement of the affected spool at the next available opportunity
and, in the interim, derating of the circuit pending replacement. Both actions
require Management of Change per SOP-ENG-12 clause 2.3, with approval by the
Chief Inspector per clause 4.4.

A vendor quotation for the replacement spool is being obtained and is expected
to fall below the fifty lakh threshold requiring Head of Department endorsement.
"""

FILES = {
    "SOP-INS-07_Piping_Inspection.txt": SOP_INSPECTION,
    "SOP-ENG-12_Management_of_Change.txt": SOP_MOC,
    "SOP-INS-11_Pressure_Vessel_Inspection.txt": VESSEL_STANDARD,
    "INS-2026-0418_Thickness_Survey_8-P-1204.txt": INSPECTION_REPORT,
    "MEMO_2026-08-30_Elbow_E-14_Deficiency.txt": CORRESPONDENCE,
}


def main() -> int:
    CORPUS.mkdir(parents=True, exist_ok=True)

    print(f"writing corpus to {CORPUS}")
    for name, body in FILES.items():
        (CORPUS / name).write_text(body, encoding="utf-8")
        print(f"  {name:<48} {len(body):>6} chars")

    if "--no-index" in sys.argv:
        print("\nfiles written; skipping indexing (--no-index)")
        return 0

    sys.path.insert(0, str(ROOT / "backend"))
    from prahari.knowledge.ingest import ingest_directory
    from prahari.knowledge.store import get_store

    print("\nindexing (first run loads bge-m3, which takes a moment) ...")
    results = ingest_directory(CORPUS, org_id="mrpl")

    for result in results:
        mark = "ok " if result.ok else "FAIL"
        print(f"  {mark} {result.filename:<48} "
              f"{result.chunks:>3} chunks  {result.embedded:>3} embedded  "
              f"{result.duration_s:>5.1f}s")
        for warning in result.warnings:
            print(f"       warning: {warning}")
        if result.error:
            print(f"       error: {result.error}")

    print(f"\nknowledge base: {get_store('mrpl').stats()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
