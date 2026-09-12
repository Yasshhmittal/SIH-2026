"""Verify reference resolution and recipe selection without a live server."""

from prahari.agent.extract import extract_values
from prahari.agent.loop import resolve_refs
from prahari.agent.recipes import select_recipe
from prahari.agent.schemas import TaskKind, TaskSpec

FLAGSHIP = (
    "Draft an approval note for the thickness deficiency found at Elbow E-14 "
    "on line 8-P-1204. Nominal wall was 8.0 mm, the latest UT reading is "
    "5.9 mm, minimum allowed is 6.4 mm, and the line has been in service "
    "7 years. Show the corrosion rate calculation."
)

print("=== extraction ===")
values = extract_values(FLAGSHIP)
print(f"  {values.as_dict()}")
print(f"  warnings: {values.warnings}")
assert values.measured_thickness_mm == 5.9, "measured must be the UT reading"
assert values.minimum_thickness_mm == 6.4, "minimum must be the retirement limit"
rate = (values.nominal_thickness_mm - values.measured_thickness_mm) / values.years_in_service
print(f"  corrosion rate = {rate} mm/yr  (expected 0.3)")
assert abs(rate - 0.3) < 1e-9

print()
print("=== recipe selection ===")
task = TaskSpec(kind=TaskKind.DOCUMENT_TO_DELIVERABLE, summary="approval note",
                needs_calculation=True, needs_retrieval=True, deliverable="docx")
recipe = select_recipe(task, values)
print(f"  selected: {recipe.name if recipe else None}")
assert recipe is not None and recipe.name == "thickness_deficiency_to_approval_note"

print()
print("=== plan built from recipe (no model call) ===")
from prahari.agent.recipes import build_plan
plan = build_plan(recipe, FLAGSHIP, task, values)
for step in plan.steps:
    print(f"  {step.id}. {step.tool:<16} {step.why[:50]}")

print()
print("=== reference resolution ===")
observations = {
    1: {"ok": True, "data": {"citations": [{"document": "SOP-INS-07", "page": 12}]}},
    2: {"ok": True, "data": {"value": 0.3, "unit": "mm/year",
                             "steps": [{"text": "= 0.3"}]}},
    3: {"ok": True, "data": {"value": 2.19, "unit": "year"}},
}
print("  single  :", resolve_refs({"x": {"$from_step": 2, "path": "data.value"}}, observations))
print("  list    :", resolve_refs({"c": {"$from_steps": [2, 3], "path": "data"}}, observations))
print("  missing :", resolve_refs({"x": {"$from_step": 99, "path": "data"}}, observations))
print("  nested  :", resolve_refs({"a": [{"v": {"$from_step": 3, "path": "data.value"}}]}, observations))
print("  literal :", resolve_refs("plain", observations))

print()
print("=== implausible parse declines the recipe ===")
bad = extract_values("nominal 5.0 mm but measured 9.0 mm and 7 years in service")
print(f"  warnings: {bad.warnings}")
assert bad.warnings, "measured > nominal must warn"

print()
print("ALL CHECKS PASSED")
