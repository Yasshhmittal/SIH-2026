"""Reproduce the docx.render failure from the live run, with the error shown."""

import traceback
from pathlib import Path

from prahari.agent.recipes import build_plan, select_recipe
from prahari.agent.extract import extract_values
from prahari.agent.loop import resolve_refs
from prahari.agent.schemas import TaskKind, TaskSpec
from prahari.tools import DEFAULT_GRANTS, ToolContext, registry as tools

FLAGSHIP = (
    "Draft an approval note for the thickness deficiency found at Elbow E-14 "
    "on line 8-P-1204. Nominal wall was 8.0 mm, the latest UT reading is "
    "5.9 mm, minimum allowed is 6.4 mm, and the line has been in service "
    "7 years. Show the corrosion rate calculation."
)

values = extract_values(FLAGSHIP)
task = TaskSpec(kind=TaskKind.DOCUMENT_TO_DELIVERABLE, summary="approval note",
                needs_calculation=True, needs_retrieval=True, deliverable="docx")
recipe = select_recipe(task, values)
plan = build_plan(recipe, FLAGSHIP, task, values)

ws = Path("data/runtime/check"); ws.mkdir(parents=True, exist_ok=True)
ctx = ToolContext(run_id="check", org_id="mrpl", workspace=ws, emit=lambda t, p: None)

observations: dict[int, dict] = {}
for step in plan.steps:
    resolved = resolve_refs(step.args, observations)
    print(f"--- step {step.id}: {step.tool}")
    print(f"    resolved args: {resolved}")

    if step.id == 4:
        spec = tools.get("docx.render")
        try:
            obs = spec.handler(ctx, **resolved)
            print(f"    ok={obs.ok} summary={obs.summary}")
        except Exception:
            print("    RAW EXCEPTION:")
            traceback.print_exc()
        break

    obs = tools.invoke(step.tool, ctx, resolved, DEFAULT_GRANTS)
    print(f"    ok={obs.ok} summary={obs.summary}")
    if not obs.ok:
        print(f"    error={obs.error}")
    observations[step.id] = {"id": step.id, "tool": step.tool, "ok": obs.ok,
                             "summary": obs.summary, "data": obs.data,
                             "error": obs.error}
