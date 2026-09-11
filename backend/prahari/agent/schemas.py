"""Typed contracts for the agent loop.

These pydantic models do double duty: they validate what comes back from the
model, and `.model_json_schema()` is handed to Ollama as a decoding constraint
so malformed output is impossible rather than merely caught.

This is the mechanism behind the project's central bet: the LLM fills in
parameters and judges outcomes; code owns the control flow.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------- intent ---

class TaskKind(str, Enum):
    """Coarse archetypes. Each may carry a plan skeleton (a "recipe")."""

    DOCUMENT_TO_DELIVERABLE = "document_to_deliverable"
    KNOWLEDGE_QA = "knowledge_qa"
    CODE_TASK = "code_task"
    VISUAL_ANALYSIS = "visual_analysis"
    CALCULATION = "calculation"
    SPREADSHEET = "spreadsheet"
    GENERAL = "general"


class TaskSpec(BaseModel):
    """The classifier's output. Constrained-decoded, so always well-formed."""

    kind: TaskKind = Field(description="Which archetype this request matches")
    summary: str = Field(description="One sentence restating the user's goal")
    needs_vision: bool = Field(
        default=False,
        description="True if an image or scanned page must actually be looked at",
    )
    needs_code: bool = Field(
        default=False, description="True if code must be written or executed"
    )
    needs_retrieval: bool = Field(
        default=True, description="True if org documents must be consulted"
    )
    needs_calculation: bool = Field(
        default=False, description="True if numeric computation is required"
    )
    deliverable: Literal["docx", "xlsx", "pptx", "code", "answer", "none"] = Field(
        default="answer", description="What artifact the user expects back"
    )


# ----------------------------------------------------------------- plan ---

class PlanStep(BaseModel):
    """One node of the plan DAG.

    `tool` is validated against the tool registry *before* execution, so a
    hallucinated tool name is rejected at plan time, not at call time.
    """

    id: int = Field(description="1-based step number")
    tool: str = Field(description="Exact tool name from the available tool list")
    why: str = Field(description="One short sentence: why this step is needed")
    args: dict[str, Any] = Field(
        default_factory=dict, description="Arguments for the tool"
    )
    depends_on: list[int] = Field(
        default_factory=list, description="Step ids whose output this step needs"
    )


class Plan(BaseModel):
    goal: str = Field(description="Restatement of what the finished work must be")
    steps: list[PlanStep] = Field(description="Ordered steps, 1-based ids")


# ---------------------------------------------------------- observations ---

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"


class Observation(BaseModel):
    """What a tool actually returned. Never free text — always structured."""

    ok: bool
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0


class CriticVerdict(BaseModel):
    """The Critic's postcondition check on a completed step."""

    passed: bool = Field(description="Did the step satisfy its postconditions")
    reason: str = Field(description="One sentence explaining the verdict")
    should_replan: bool = Field(
        default=False, description="True if the remaining plan must change"
    )


class ReplanPatch(BaseModel):
    """A bounded edit to the *remaining* plan, never a whole new plan."""

    rationale: str = Field(description="Why the plan must change")
    replace_from_step: int = Field(description="First step id to discard")
    new_steps: list[PlanStep] = Field(description="Steps to run instead")


# ------------------------------------------------------------- findings ---

class Finding(BaseModel):
    """One extracted inspection finding. Shape is deliberately industrial."""

    location: str = Field(description="Equipment tag or location, e.g. 'Elbow E-14'")
    description: str = Field(description="What was observed")
    nominal_thickness_mm: float | None = None
    measured_thickness_mm: float | None = None
    minimum_thickness_mm: float | None = None
    years_in_service: float | None = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    source_page: int | None = Field(
        default=None, description="Page of the source document this came from"
    )


class FindingSet(BaseModel):
    findings: list[Finding]


# ---------------------------------------------------------------- utils ---

def schema_of(model: type[BaseModel]) -> dict[str, Any]:
    """JSON Schema for Ollama's constrained decoding."""
    return model.model_json_schema()
