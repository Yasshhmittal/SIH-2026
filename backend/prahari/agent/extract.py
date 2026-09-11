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

# Phrases that label a thickness, so we can tell nominal from measured from
# minimum. Ordered by specificity: the most explicit label wins.
_THICKNESS_LABELS: list[tuple[str, str]] = [
    (r"nominal(?:\s+(?:wall|thickness))?", "nominal_thickness_mm"),
    (r"(?:minimum|min|retirement|allowed|allowable)(?:\s+(?:wall|thickness))?",
     "minimum_thickness_mm"),
    (r"(?:measured|actual|latest|current|ut\s+reading|reading|observed)",
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


def _accumulate_thicknesses(text: str) -> dict[str, float]:
    """Attribute each stated thickness to its nearest preceding label."""
    assignments: dict[str, float] = {}
    for match in re.finditer(_MM, text, flags=re.IGNORECASE):
        value = float(match.group(1))
        prefix = text[max(0, match.start() - 48):match.start()].lower()

        assigned = False
        for label_pattern, key in _THICKNESS_LABELS:
            if key in assignments:
                continue
            if re.search(label_pattern, prefix):
                assignments[key] = value
                assigned = True
                break
        if not assigned and "unlabelled" not in assignments:
            assignments["unlabelled"] = value
    return assignments


def extract_values(prompt: str) -> ExtractedValues:
    text = prompt

    thicknesses = _accumulate_thicknesses(text)
    result = ExtractedValues(
        nominal_thickness_mm=thicknesses.get("nominal_thickness_mm"),
        measured_thickness_mm=thicknesses.get("measured_thickness_mm"),
        minimum_thickness_mm=thicknesses.get("minimum_thickness_mm"),
    )

    # Unlabelled values fill the obvious gaps: the largest is nominal, the
    # smallest is the floor. This is a fallback, never an override.
    unlabelled = thicknesses.get("unlabelled")
    if unlabelled is not None:
        if result.nominal_thickness_mm is None:
            result.nominal_thickness_mm = unlabelled
        elif result.measured_thickness_mm is None:
            result.measured_thickness_mm = unlabelled
        elif result.minimum_thickness_mm is None:
            result.minimum_thickness_mm = unlabelled
        else:
            result.other_thicknesses.append(unlabelled)

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

    return result
