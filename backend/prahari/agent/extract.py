"""Deterministic extraction of concrete values from the request.

Small planners are unreliable at *inventing* arguments but reliable at *copying*
them once they are placed in front of them. So values that are literally present
in the user's request — thicknesses, years in service, equipment tags, line
numbers — are parsed here and injected into the planning prompt and into recipe
step arguments.

Nothing is inferred. If a number is not stated, it is not produced.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_MM = r"(\d+(?:\.\d+)?)\s*(?:mm|millimet(?:er|re)s?)"
_YEARS = r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)"

# Phrases that label a thickness. Word boundaries are essential: without them
# "min" matches inside "Nominal", which silently swaps the measured and
# minimum readings and corrupts every downstream calculation.
_THICKNESS_LABELS: list[tuple[str, str]] = [
    (r"\bnominal\b(?:\s+(?:wall|thickness))?", "nominal_thickness_mm"),
    (r"\b(?:minimum|min|retirement|allowed|allowable|limit)\b(?:\s+(?:wall|thickness))?",
     "minimum_thickness_mm"),
    (r"\b(?:measured|actual|latest|current|ut\s+reading|reading|observed|survey)\b",
     "measured_thickness_mm"),
]

_TAG = r"\b([A-Z]{1,4}[-–]?\d{1,4}[A-Z]?)\b"
_LINE = r"\b(\d{1,2}[-–][A-Z]{1,3}[-–]\d{2,5}[A-Z]?)\b"


@dataclass
class ExtractedValues:
    """Concrete values found in the request. Absent means absent."""

    nominal_thickness_mm: float | None = None
    measured_thickness_mm: float | None = None
    minimum_thickness_mm: float | None = None
    years_in_service: float | None = None
    equipment_tag: str | None = None
    line_number: str | None = None
    other_thicknesses: list[float] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "nominal_thickness_mm": self.nominal_thickness_mm,
                "measured_thickness_mm": self.measured_thickness_mm,
                "minimum_thickness_mm": self.minimum_thickness_mm,
                "years_in_service": self.years_in_service,
                "equipment_tag": self.equipment_tag,
                "line_number": self.line_number,
            }.items()
            if value is not None
        }

    def as_prompt_evidence(self) -> str:
        found = self.as_dict()
        if not found:
            return ""
        pretty = ", ".join(f"{k}={v}" for k, v in found.items())
        return f"Concrete values stated in the request: {pretty}."

    @property
    def has_full_thickness_set(self) -> bool:
        return (
            self.nominal_thickness_mm is not None
            and self.measured_thickness_mm is not None
            and self.years_in_service is not None
        )


def _accumulate_thicknesses(text: str) -> tuple[dict[str, float], list[float]]:
    """Attribute each stated thickness to its NEAREST preceding label.

    Proximity, not list order. "Nominal wall was 8.0 mm, the latest UT reading
    is 5.9 mm, minimum allowed is 6.4 mm" has three labels in one sentence, and
    taking the first matching pattern rather than the closest one assigns 5.9
    to whichever label happens to sit earlier in the list.

    Each number claims its nearest label; where two numbers claim the same
    label, the closer one keeps it.
    """
    # (key, value, distance-from-number)
    claims: list[tuple[str, float, int]] = []
    unlabelled: list[float] = []

    for match in re.finditer(_MM, text, flags=re.IGNORECASE):
        value = float(match.group(1))
        window_start = max(0, match.start() - 60)
        prefix = text[window_start:match.start()].lower()

        best_key: str | None = None
        best_end = -1
        for label_pattern, key in _THICKNESS_LABELS:
            for label in re.finditer(label_pattern, prefix):
                if label.end() > best_end:
                    best_end, best_key = label.end(), key

        if best_key is None:
            unlabelled.append(value)
        else:
            claims.append((best_key, value, len(prefix) - best_end))

    assignments: dict[str, float] = {}
    distances: dict[str, int] = {}
    for key, value, distance in claims:
        if key not in assignments or distance < distances[key]:
            assignments[key] = value
            distances[key] = distance

    return assignments, unlabelled


def extract_values(prompt: str) -> ExtractedValues:
    text = prompt

    thicknesses, unlabelled = _accumulate_thicknesses(text)
    result = ExtractedValues(
        nominal_thickness_mm=thicknesses.get("nominal_thickness_mm"),
        measured_thickness_mm=thicknesses.get("measured_thickness_mm"),
        minimum_thickness_mm=thicknesses.get("minimum_thickness_mm"),
    )

    # Unlabelled values fill gaps in order. A fallback, never an override.
    for value in unlabelled:
        if result.nominal_thickness_mm is None:
            result.nominal_thickness_mm = value
        elif result.measured_thickness_mm is None:
            result.measured_thickness_mm = value
        elif result.minimum_thickness_mm is None:
            result.minimum_thickness_mm = value
        else:
            result.other_thicknesses.append(value)

    years = re.search(_YEARS, text, flags=re.IGNORECASE)
    if years:
        result.years_in_service = float(years.group(1))

    # Equipment tags: prefer one introduced by "at/on/for", else the first seen.
    tags = re.findall(_TAG, text)
    noise = {"MM", "SOP", "API", "UT", "OEM", "PDF", "ID", "OK"}
    tags = [t for t in tags if t.upper() not in noise]
    if tags:
        contextual = re.search(
            r"(?:at|on|for)\s+(?:elbow|valve|line|pump|vessel|tank|nozzle|pipe)?\s*"
            + _TAG,
            text, flags=re.IGNORECASE,
        )
        result.equipment_tag = contextual.group(1) if contextual else tags[0]

    line = re.search(_LINE, text)
    if line:
        result.line_number = line.group(1)

    result.warnings = _check_plausibility(result)
    return result


def _check_plausibility(values: ExtractedValues) -> list[str]:
    """Flag physically implausible attributions rather than silently fixing them.

    Nominal is the as-built thickness, so it must be the largest of the three.
    A violation means the labels were attributed wrongly — and a wrong
    attribution produces a confident, wrong corrosion rate, which is exactly
    the failure this system exists to prevent. Reordering the values here would
    hide the parse error; surfacing it lets the caller decline the recipe.
    """
    warnings: list[str] = []
    nominal = values.nominal_thickness_mm
    measured = values.measured_thickness_mm
    minimum = values.minimum_thickness_mm

    if nominal is not None and measured is not None and measured > nominal:
        warnings.append(
            f"measured ({measured} mm) exceeds nominal ({nominal} mm) — "
            "thickness labels may have been misread"
        )
    if nominal is not None and minimum is not None and minimum > nominal:
        warnings.append(
            f"minimum ({minimum} mm) exceeds nominal ({nominal} mm) — "
            "thickness labels may have been misread"
        )
    return warnings
