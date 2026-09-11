"""Deterministic calculation tool.

The LLM never does arithmetic in PRAHARI. In a refinery, a hallucinated decimal
place is a safety incident, so numbers are computed by sympy with units carried
by pint, and every intermediate step is returned as data.

That is also what satisfies the problem statement's "calculations with steps
shown" — the steps are a list of records, not a sentence the model wrote.
"""

from __future__ import annotations

import json
from typing import Any

import pint
import sympy as sp

from ..agent.schemas import Observation
from .base import CAP_COMPUTE, ToolContext, ToolSpec, registry

_ureg = pint.UnitRegistry()

# Named formulas an org can extend via orgs/<id>/standards/calc_library.yaml.
# Shipped defaults are the API 510/570-shaped inspection calculations.
BUILTIN_FORMULAS: dict[str, dict[str, Any]] = {
    "corrosion_rate": {
        "expr": "(t_nominal - t_measured) / years",
        "units": "mm / year",
        "description": "Uniform corrosion rate from thickness loss over time",
        "inputs": {
            "t_nominal": "mm", "t_measured": "mm", "years": "year",
        },
        "example": {"t_nominal": 8.0, "t_measured": 5.9, "years": 7.0},
    },
    "remaining_life": {
        "expr": "(t_measured - t_minimum) / corrosion_rate",
        "units": "year",
        "description": "Years until measured thickness reaches the retirement limit",
        "inputs": {
            "t_measured": "mm", "t_minimum": "mm", "corrosion_rate": "mm / year",
        },
        "example": {"t_measured": 5.9, "t_minimum": 6.4, "corrosion_rate": 0.3},
    },
    "next_inspection_interval": {
        "expr": "remaining_life / 2",
        "units": "year",
        "description": "Half remaining life, the conventional inspection interval",
        "inputs": {"remaining_life": "year"},
        "example": {"remaining_life": 4.0},
    },
}


def _evaluate(expr: str, variables: dict[str, float]) -> tuple[float, list[dict]]:
    """Evaluate with sympy, returning the value and a substitution trace."""
    symbols = {name: sp.Symbol(name) for name in variables}
    parsed = sp.sympify(expr, locals=symbols)

    steps: list[dict[str, Any]] = [
        {"stage": "formula", "text": f"expression: {parsed}"}
    ]

    subs_text = ", ".join(f"{k} = {v}" for k, v in variables.items())
    steps.append({"stage": "substitute", "text": f"substitute {subs_text}"})

    substituted = parsed.subs({symbols[k]: v for k, v in variables.items()})
    steps.append({"stage": "substituted", "text": f"= {substituted}"})

    value = float(sp.N(substituted))
    steps.append({"stage": "result", "text": f"= {value:.6g}"})
    return value, steps


def _normalise_formula_name(name: str) -> str:
    """Accept 'Corrosion Rate', 'corrosion-rate', 'corrosion rate' as one thing.

    A 3B planner will not reproduce a snake_case identifier reliably, and
    failing a step over punctuation is a waste of a model call.
    """
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _formula_catalogue() -> str:
    """Signatures for the planner, with a concrete example per formula.

    The example matters. Given only `corrosion_rate(t_nominal in mm, ...)` a
    1.5B planner copies the signature text into the argument value. A literal
    filled-in object shows the expected *shape*.
    """
    lines = []
    for name, spec in BUILTIN_FORMULAS.items():
        args = ", ".join(f"{k} in {v}" for k, v in spec["inputs"].items())
        lines.append(
            f"\n  {name}({args}) -> {spec['units']}\n"
            f"      example variables: {json.dumps(spec['example'])}"
        )
    return "".join(lines)


def calc_evaluate(
    ctx: ToolContext,
    *,
    formula: str | None = None,
    expression: str | None = None,
    variables: dict[str, float] | None = None,
    unit: str | None = None,
) -> Observation:
    """Evaluate a named formula or a raw expression, deterministically.

    Either `formula` (from the library) or `expression` (arbitrary) must be
    given. `variables` maps symbol names to numeric values.
    """
    try:
        variables = {k: float(v) for k, v in (variables or {}).items()}
    except (TypeError, ValueError) as exc:
        return Observation(ok=False, error=f"variables must be numeric: {exc}",
                           summary="non-numeric input")

    if formula:
        key = _normalise_formula_name(formula)
        spec = BUILTIN_FORMULAS.get(key)
        if spec is None:
            return Observation(
                ok=False,
                error=(
                    f"unknown formula '{formula}'. Available: "
                    f"{_formula_catalogue()}"
                ),
                summary="unknown formula",
                data={"available": sorted(BUILTIN_FORMULAS)},
            )
        expr = spec["expr"]
        result_unit = unit or spec["units"]
        description = spec["description"]
        formula = key
    elif expression:
        expr = expression
        result_unit = unit or ""
        description = "ad-hoc expression"
    else:
        return Observation(ok=False, error="provide either 'formula' or 'expression'",
                           summary="nothing to evaluate")

    try:
        required = {str(s) for s in sp.sympify(expr).free_symbols}
    except Exception as exc:
        return Observation(ok=False, error=f"cannot parse expression: {exc}",
                           summary="parse error")

    missing = required - set(variables)
    if missing:
        return Observation(
            ok=False,
            error=f"missing variables: {', '.join(sorted(missing))}",
            summary="missing inputs",
        )

    try:
        value, steps = _evaluate(expr, variables)
    except ZeroDivisionError:
        return Observation(ok=False, error="division by zero", summary="undefined")
    except Exception as exc:
        return Observation(ok=False, error=f"evaluation failed: {exc}",
                           summary="evaluation error")

    pretty = f"{value:.4g}"
    if result_unit:
        try:
            quantity = value * _ureg(result_unit)
            pretty = f"{quantity:~P.4g}"
        except Exception:
            pretty = f"{value:.4g} {result_unit}"

    return Observation(
        ok=True,
        summary=f"{formula or 'expression'} = {pretty}",
        data={
            "formula": formula,
            "expression": expr,
            "description": description,
            "variables": variables,
            "value": value,
            "unit": result_unit,
            "formatted": pretty,
            "steps": steps,
        },
    )


registry.register(
    ToolSpec(
        name="calc.evaluate",
        description=(
            "Compute a value deterministically with units, showing every step. "
            "Pass `formula` plus `variables` using EXACTLY these names — "
            + _formula_catalogue()
            + ". Or pass `expression` for ad-hoc maths."
        ),
        args_schema={
            "type": "object",
            "properties": {
                "formula": {
                    "type": "string",
                    "enum": sorted(BUILTIN_FORMULAS),
                    "description": "Named formula from the library",
                },
                "expression": {"type": "string",
                               "description": "Raw expression, if no named formula"},
                "variables": {
                    "type": "object",
                    "description": (
                        "Symbol name -> number. Names must match the formula "
                        "signature exactly, e.g. corrosion_rate needs "
                        "t_nominal, t_measured, years"
                    ),
                },
                "unit": {"type": "string", "description": "Override result unit"},
            },
            "required": ["variables"],
        },
        capabilities=frozenset({CAP_COMPUTE}),
        handler=calc_evaluate,
        returns="value, unit, formatted string, and an ordered list of steps",
    )
)
