"""Deterministic request signals.

A 3B classifier is good at gist and unreliable on specifics: it read "draft an
approval note ... show the corrosion rate calculation" and returned
`deliverable=code, needs_calculation=False`. Both are recoverable from the text
by inspection, so code recovers them.

Two uses, in this order:

1. **Evidence.** Signals go into the classify prompt so the model starts from
   observations rather than a cold read.
2. **Reconciliation.** After classification, an explicit phrase overrides a
   contradicting flag — and the override is published as an event, so a
   correction is always visible rather than silent.

This is the project's central bet applied to classification: the model judges,
code owns the outcome.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .schemas import TaskSpec

# (regex, value, human label). Ordered: the first match wins for deliverables.
_DELIVERABLE_PATTERNS: list[tuple[str, str, str]] = [
    (r"\bapproval note\b|\bnoting sheet\b|\bapproval memo\b", "docx", "approval note"),
    (r"\bboard (presentation|deck)\b|\bslide deck\b|\bpresentation\b|\bppt\b|\bslides\b",
     "pptx", "presentation"),
    (r"\bspreadsheet\b|\bexcel\b|\bxlsx\b|\bworkbook\b", "xlsx", "spreadsheet"),
    (r"\bword (file|document)\b|\bdocx\b|\bdraft (a |an )?(note|letter|memo|report)\b",
     "docx", "word document"),
    (r"\bwrite (a |an )?(script|program|function|python)\b|\bpython script\b",
     "code", "code request"),
]

_CALCULATION = (
    r"\bcalculat(e|ion|ions)\b|\bcomput(e|ation)\b|\bcorrosion rate\b|"
    r"\bremaining life\b|\bthickness\b|\bwith steps\b|\bshow the (working|math|steps)\b"
)
_VISION = (
    r"\bscan(ned|s)?\b|\bdrawing(s)?\b|\bp&id\b|\bpid\b|\bimage\b|\bphoto(graph)?\b|"
    r"\bhandwritten\b|\bdiagram\b|\bsketch\b|\bisometric\b"
)
_CODE = r"\bscript\b|\bcode\b|\bpython\b|\bunit test(s)?\b|\bpytest\b|\bprogram\b"
_RETRIEVAL = (
    r"\bsop\b|\bmanual(s)?\b|\bstandard(s)?\b|\bprocedure(s)?\b|\bas per\b|"
    r"\bper our\b|\bpolicy\b|\bguideline(s)?\b|\bapi \d{3}\b"
)


@dataclass
class Signals:
    deliverable: str | None = None
    needs_calculation: bool = False
    needs_vision: bool = False
    needs_code: bool = False
    needs_retrieval: bool = False
    matched: dict[str, str] = field(default_factory=dict)

    def as_prompt_evidence(self) -> str:
        """Compact evidence block for the classifier. Empty when nothing matched."""
        if not self.matched:
            return ""
        bits = [f"{key} (matched: {phrase!r})" for key, phrase in self.matched.items()]
        return "Detected in the request: " + "; ".join(bits)

    def to_dict(self) -> dict[str, Any]:
        return {
            "deliverable": self.deliverable,
            "needs_calculation": self.needs_calculation,
            "needs_vision": self.needs_vision,
            "needs_code": self.needs_code,
            "needs_retrieval": self.needs_retrieval,
            "matched": self.matched,
        }


def _search(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(0) if match else None


def detect_signals(prompt: str) -> Signals:
    signals = Signals()
    text = prompt.lower()

    for pattern, value, label in _DELIVERABLE_PATTERNS:
        hit = _search(pattern, text)
        if hit:
            signals.deliverable = value
            signals.matched[f"deliverable={value}"] = hit
            break

    for pattern, attr in (
        (_CALCULATION, "needs_calculation"),
        (_VISION, "needs_vision"),
        (_CODE, "needs_code"),
        (_RETRIEVAL, "needs_retrieval"),
    ):
        hit = _search(pattern, text)
        if hit:
            setattr(signals, attr, True)
            signals.matched[attr] = hit

    return signals


def reconcile(task: TaskSpec, signals: Signals) -> tuple[TaskSpec, list[dict[str, str]]]:
    """Override the classifier where an explicit phrase contradicts it.

    Deliberately one-directional: an explicit phrase can turn a flag ON or
    correct a deliverable, but absence of a phrase never turns a flag OFF. The
    model may have inferred something real that no regex covers.
    """
    corrections: list[dict[str, str]] = []
    patch: dict[str, Any] = {}

    if signals.deliverable and task.deliverable != signals.deliverable:
        corrections.append({
            "field": "deliverable",
            "from": task.deliverable,
            "to": signals.deliverable,
            "evidence": signals.matched.get(f"deliverable={signals.deliverable}", ""),
        })
        patch["deliverable"] = signals.deliverable

    for attr in ("needs_calculation", "needs_vision", "needs_code", "needs_retrieval"):
        if getattr(signals, attr) and not getattr(task, attr):
            corrections.append({
                "field": attr,
                "from": "false",
                "to": "true",
                "evidence": signals.matched.get(attr, ""),
            })
            patch[attr] = True

    if not patch:
        return task, corrections
    return task.model_copy(update=patch), corrections
