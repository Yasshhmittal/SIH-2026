"""Extraction tests.

These exist because of a real defect: "Nominal wall was 8.0 mm, the latest UT
reading is 5.9 mm, minimum allowed is 6.4 mm" parsed as measured=6.4,
minimum=5.9. The two readings were swapped, and the run went on to report a
corrosion rate of 0.2286 mm/yr instead of 0.3 — confidently, with steps shown,
in a Word file for signature.

A wrong number that looks right is the worst failure this system can produce,
so the attribution logic is pinned here.
"""

from __future__ import annotations

import pytest

from prahari.agent.extract import extract_values

FLAGSHIP = (
    "Draft an approval note for the thickness deficiency found at Elbow E-14 "
    "on line 8-P-1204. Nominal wall was 8.0 mm, the latest UT reading is "
    "5.9 mm, minimum allowed is 6.4 mm, and the line has been in service "
    "7 years. Show the corrosion rate calculation."
)


def test_flagship_prompt_attributes_every_thickness_correctly():
    values = extract_values(FLAGSHIP)

    assert values.nominal_thickness_mm == 8.0
    assert values.measured_thickness_mm == 5.9   # the UT reading
    assert values.minimum_thickness_mm == 6.4    # the retirement limit
    assert values.years_in_service == 7.0
    assert values.equipment_tag == "E-14"
    assert values.line_number == "8-P-1204"
    assert values.warnings == []


def test_corrosion_rate_from_extracted_values_is_correct():
    """The number that reaches the Word file must be right."""
    values = extract_values(FLAGSHIP)
    rate = (values.nominal_thickness_mm - values.measured_thickness_mm) / values.years_in_service
    assert rate == pytest.approx(0.3, abs=1e-9)


def test_min_inside_nominal_does_not_steal_the_label():
    """'Nominal' contains 'min'. Without word boundaries it matched."""
    values = extract_values("Nominal wall 10.0 mm, measured 9.1 mm.")
    assert values.nominal_thickness_mm == 10.0
    assert values.measured_thickness_mm == 9.1
    assert values.minimum_thickness_mm is None


@pytest.mark.parametrize(
    "prompt,nominal,measured,minimum",
    [
        ("nominal 12.7 mm, actual 11.2 mm, retirement limit 9.5 mm",
         12.7, 11.2, 9.5),
        ("as-built nominal thickness 8.0 mm; current reading 7.1 mm",
         8.0, 7.1, None),
        ("survey found 6.2 mm against a nominal 8.0 mm",
         8.0, 6.2, None),
        ("minimum allowable thickness is 6.4 mm", None, None, 6.4),
    ],
)
def test_label_variants(prompt, nominal, measured, minimum):
    values = extract_values(prompt)
    assert values.nominal_thickness_mm == nominal
    assert values.measured_thickness_mm == measured
    assert values.minimum_thickness_mm == minimum


def test_nearest_label_wins_when_several_share_a_sentence():
    values = extract_values(
        "measured at 5.0 mm where the minimum is 6.0 mm and nominal was 8.0 mm"
    )
    assert values.measured_thickness_mm == 5.0
    assert values.minimum_thickness_mm == 6.0
    assert values.nominal_thickness_mm == 8.0


def test_implausible_attribution_is_flagged_not_silently_fixed():
    """Measured above nominal is physically impossible — say so."""
    values = extract_values("nominal 5.0 mm but measured 9.0 mm")
    assert values.warnings
    assert "measured" in values.warnings[0]
    # The values are left as parsed; the caller decides what to do.
    assert values.measured_thickness_mm == 9.0


def test_absent_values_stay_absent():
    """Nothing is inferred. No number stated means no number produced."""
    values = extract_values("Summarise the latest inspection report.")
    assert values.nominal_thickness_mm is None
    assert values.measured_thickness_mm is None
    assert values.years_in_service is None
    assert not values.has_full_thickness_set


def test_units_written_out_are_recognised():
    values = extract_values("nominal wall 8.0 millimetres, measured 6.5 millimeters")
    assert values.nominal_thickness_mm == 8.0
    assert values.measured_thickness_mm == 6.5


def test_full_set_gate_requires_the_three_recipe_inputs():
    partial = extract_values("nominal 8.0 mm, measured 5.9 mm")
    assert not partial.has_full_thickness_set   # no years in service

    complete = extract_values("nominal 8.0 mm, measured 5.9 mm, 7 years in service")
    assert complete.has_full_thickness_set
