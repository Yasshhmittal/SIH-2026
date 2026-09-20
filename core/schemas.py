"""
core/schemas.py — Structured result definitions for NEBULA pipeline.

All data flowing between pipeline stages uses these dataclasses / TypedDicts
so every component has a clear contract and the validator can check them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional


# ── Document processing ───────────────────────────────────────────────────────

@dataclass
class PageRecord:
    """Represents one extracted page from a document."""
    document: str                        # source filename
    page: int                            # 1-indexed
    text: str                            # extracted / OCR text
    source_type: Literal["native", "ocr"]
    ocr_confidence: Optional[float] = None  # 0.0–1.0 if OCR, else None
    image_path: Optional[str] = None     # path to rendered page image (if any)
    visual_observations: List["VisualObservation"] = field(default_factory=list)


@dataclass
class VisualObservation:
    """Single observation produced by Qwen2.5-VL."""
    text: str
    page: int
    confidence: Literal["high", "medium", "low"] = "medium"
    source_model: str = "Qwen2.5-VL-7B"


# ── RAG / Retrieval ───────────────────────────────────────────────────────────

@dataclass
class Chunk:
    """A text chunk ready for embedding."""
    chunk_id: str
    document: str
    page: int
    text: str
    source_type: Literal["native", "ocr"] = "native"


@dataclass
class RetrievedChunk:
    """A chunk returned by the retrieval step, with its similarity score."""
    chunk: Chunk
    score: float                         # cosine similarity 0.0–1.0


# ── Reasoning / Grounding ─────────────────────────────────────────────────────

@dataclass
class EvidenceSource:
    document: str
    page: int
    evidence: str                        # verbatim excerpt used


@dataclass
class GroundedClaim:
    claim: str
    status: Literal["supported", "inference", "uncertain", "missing"]
    sources: List[EvidenceSource] = field(default_factory=list)


@dataclass
class ReasoningResult:
    """Structured output from Qwen2.5-7B reasoning step."""
    task_class: str
    supported_findings: List[GroundedClaim] = field(default_factory=list)
    inferences: List[GroundedClaim] = field(default_factory=list)
    uncertainties: List[GroundedClaim] = field(default_factory=list)
    recommended_action: str = ""
    raw_json: Optional[str] = None       # original model output for audit


# ── Validation ────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    passed: bool
    unsupported_count: int = 0
    invalid_citations: List[str] = field(default_factory=list)
    missing_evidence: bool = False
    warnings: List[str] = field(default_factory=list)
    failure_reason: Optional[str] = None


# ── Agent state ───────────────────────────────────────────────────────────────

@dataclass
class AgentState:
    """Carries all intermediate results through the agent pipeline."""
    task: str = ""
    inspection_path: Optional[str] = None
    sop_path: Optional[str] = None

    # Router decision — populated after CLASSIFY (surfaced in the UI)
    doc_info: Optional[dict] = None          # classify_document() output
    router_plan: Optional[dict] = None       # build_component_plan() output

    # Pipeline stages — populated as the agent runs
    pages: List[PageRecord] = field(default_factory=list)
    chunks: List[Chunk] = field(default_factory=list)
    retrieved: List[RetrievedChunk] = field(default_factory=list)
    reasoning: Optional[ReasoningResult] = None
    validation: Optional[ValidationResult] = None
    docx_path: Optional[str] = None

    # First fatal error that aborted the pipeline (None if it ran to completion)
    error: Optional[str] = None

    # Timeline events shown in UI
    events: List[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        """Append a timestamped event to the agent timeline."""
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.events.append(f"[{ts}] {msg}")
