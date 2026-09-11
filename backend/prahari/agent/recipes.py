"""Plan recipes — deterministic skeletons for known task archetypes.

The freehand planner is genuinely unreliable at 3B: across runs it invented
formula names, then dropped the calculation step entirely rather than fix it,
and each attempt cost ~55s. Both failures share a cause — it was being asked to
design control flow, which is the one thing the architecture says it should not
do (see docs/context.md D1).

So for archetypes we recognise, the *shape* of the plan is code and the model's
job shrinks to classification. A recipe is selected only when its required
values were actually found in the request, and the UI labels the plan with the
recipe that produced it. When nothing matches, the freehand planner still runs.

Step arguments may reference earlier observations:

    {"$from_step": 2, "path": "data.value"}      -> that step's value
    {"$from_steps": [2, 3], "path": "data"}      -> list of those steps' data

References are resolved by the executor immediately before invocation, so a
step always sees real values rather than a promise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .extract import ExtractedValues
from .schemas import Plan, PlanStep, TaskKind, TaskSpec


def from_step(step_id: int, path: str) -> dict[str, Any]:
    return {"$from_step": step_id, "path": path}


def from_steps(step_ids: list[int], path: str) -> dict[str, Any]:
    return {"$from_steps": step_ids, "path": path}


@dataclass(frozen=True)
class Recipe:
    name: str
    description: str
    matches: Callable[[TaskSpec, ExtractedValues], bool]
    build: Callable[[str, TaskSpec, ExtractedValues], list[PlanStep]]


# ------------------------------------- inspection report -> approval note ---

def _matches_thickness_note(task: TaskSpec, values: ExtractedValues) -> bool:
    return (
        task.deliverable == "docx"
        and task.needs_calculation
        and values.has_full_thickness_set
    )


def _build_thickness_note(
    prompt: str, task: TaskSpec, values: ExtractedValues
) -> list[PlanStep]:
    """The flagship: thickness deficiency -> cited, calculated approval note."""
    location = values.equipment_tag or values.line_number or "the affected component"
    subject = " ".join(
        part for part in [values.line_number, values.equipment_tag] if part
    ) or location

    search_terms = " ".join(
        part for part in [
            "minimum retirement thickness piping inspection criterion",
            values.line_number or "",
        ] if part
    ).strip()

    steps = [
        PlanStep(
            id=1,
            tool="kb.search",
            why="Find the governing retirement-thickness criterion in the SOPs",
            args={"query": search_terms, "k": 6},
        ),
        PlanStep(
            id=2,
            tool="calc.evaluate",
            why="Compute the uniform corrosion rate from the thickness loss",
            args={
                "formula": "corrosion_rate",
                "variables": {
                    "t_nominal": values.nominal_thickness_mm,
                    "t_measured": values.measured_thickness_mm,
                    "years": values.years_in_service,
                },
            },
        ),
    ]

    calc_step_ids = [2]

    # Remaining life needs a retirement limit; only plan it if one was stated.
    if values.minimum_thickness_mm is not None:
        steps.append(
            PlanStep(
                id=3,
                tool="calc.evaluate",
                why="Compute remaining life against the retirement limit",
                args={
                    "formula": "remaining_life",
                    "variables": {
                        "t_measured": values.measured_thickness_mm,
                        "t_minimum": values.minimum_thickness_mm,
                        "corrosion_rate": from_step(2, "data.value"),
                    },
                },
                depends_on=[2],
            )
        )
        calc_step_ids.append(3)

    finding: dict[str, Any] = {
        "location": location,
        "description": (
            f"Measured wall thickness {values.measured_thickness_mm} mm against "
            f"nominal {values.nominal_thickness_mm} mm"
            + (
                f"; retirement limit {values.minimum_thickness_mm} mm"
                if values.minimum_thickness_mm is not None else ""
            )
        ),
        "nominal_thickness_mm": values.nominal_thickness_mm,
        "measured_thickness_mm": values.measured_thickness_mm,
        "minimum_thickness_mm": values.minimum_thickness_mm,
        "years_in_service": values.years_in_service,
        "severity": (
            "critical"
            if (values.minimum_thickness_mm is not None
                and values.measured_thickness_mm is not None
                and values.measured_thickness_mm < values.minimum_thickness_mm)
            else "high"
        ),
    }

    below_limit = finding["severity"] == "critical"
    recommendation = (
        f"Measured thickness at {location} is below the stated retirement limit. "
        "Recommend derating or replacing the affected spool before the next run, "
        "raised as a work order under management of change."
        if below_limit else
        f"Continue monitoring {location} at the calculated inspection interval "
        "and re-survey at the next opportunity."
    )

    steps.append(
        PlanStep(
            id=len(steps) + 1,
            tool="docx.render",
            why="Produce the approval note with findings, calculations and sources",
            args={
                "title": f"Approval Note — Thickness Deficiency, {subject}",
                "summary": (
                    f"Ultrasonic survey of {subject} records wall thickness of "
                    f"{values.measured_thickness_mm} mm against a nominal "
                    f"{values.nominal_thickness_mm} mm after "
                    f"{values.years_in_service} years in service."
                ),
                "findings": [finding],
                "calculations": from_steps(calc_step_ids, "data"),
                "citations": from_step(1, "data.citations"),
                "recommendation": recommendation,
            },
            depends_on=calc_step_ids + [1],
        )
    )
    return steps


# ------------------------------------------------------------ SOP question ---

def _matches_sop_question(task: TaskSpec, values: ExtractedValues) -> bool:
    return (
        task.kind == TaskKind.KNOWLEDGE_QA
        and task.needs_retrieval
        and task.deliverable in {"answer", "none"}
    )


def _build_sop_question(
    prompt: str, task: TaskSpec, values: ExtractedValues
) -> list[PlanStep]:
    return [
        PlanStep(
            id=1,
            tool="kb.search",
            why="Retrieve the passages that answer the question, with citations",
            args={"query": prompt[:240], "k": 8},
        )
    ]


# --------------------------------------------------------------- registry ---

RECIPES: list[Recipe] = [
    Recipe(
        name="thickness_deficiency_to_approval_note",
        description=(
            "Scanned/stated thickness readings become a cited approval note "
            "with corrosion rate and remaining life computed deterministically"
        ),
        matches=_matches_thickness_note,
        build=_build_thickness_note,
    ),
    Recipe(
        name="sop_question",
        description="Answer a question from the organisation's SOPs, with citations",
        matches=_matches_sop_question,
        build=_build_sop_question,
    ),
]


def select_recipe(task: TaskSpec, values: ExtractedValues) -> Recipe | None:
    for recipe in RECIPES:
        try:
            if recipe.matches(task, values):
                return recipe
        except Exception:
            continue
    return None


def build_plan(
    recipe: Recipe, prompt: str, task: TaskSpec, values: ExtractedValues
) -> Plan:
    steps = recipe.build(prompt, task, values)
    for index, step in enumerate(steps, start=1):
        step.id = index
    return Plan(goal=f"{recipe.description} — for: {prompt[:120]}", steps=steps)
