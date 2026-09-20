"""
core/validator.py — Grounding and output validation for NEBULA.

Implements the six hallucination-prevention mechanisms from §6 of the plan:
  1. Evidence-only prompting (enforced in agent.py prompt construction)
  2. Mandatory evidence — reject factual claims with no source
  3. Retrieval threshold — if similarity too low, do not proceed
  4. Source validation — document/page must exist in retrieved chunks
  5. Epistemic labels — supported / inference / uncertain / missing
  6. Human review label — always present in DOCX

This file handles mechanisms 2, 3, 4, and 5 programmatically.
"""

from __future__ import annotations

from typing import List, Set
from core.schemas import (
    PageRecord,
    ReasoningResult,
    RetrievedChunk,
    ValidationResult,
    GroundedClaim,
)

SIMILARITY_THRESHOLD = 0.35   # minimum cosine score for valid evidence


def validate_retrieval(retrieved: List[RetrievedChunk]) -> tuple[bool, str]:
    """
    Mechanism 3 — Retrieval threshold.
    Returns (ok, reason). If no chunk meets the threshold, abort reasoning.
    """
    if not retrieved:
        return False, "NO SUPPORTING EVIDENCE FOUND — retrieval returned no chunks."
    top_score = max(c.score for c in retrieved)
    if top_score < SIMILARITY_THRESHOLD:
        return False, (
            f"NO SUPPORTING EVIDENCE FOUND — best similarity score {top_score:.3f} "
            f"is below threshold {SIMILARITY_THRESHOLD}."
        )
    return True, ""


def _build_valid_citations(retrieved: List[RetrievedChunk], pages: List[PageRecord]) -> Set[tuple]:
    """Build the set of (document, page) pairs that actually exist in retrieved chunks or observed pages."""
    valid = {(c.chunk.document, c.chunk.page) for c in retrieved}
    valid.update((p.document, p.page) for p in pages)
    return valid


def _validate_claim(
    claim: GroundedClaim,
    valid_citations: Set[tuple],
    require_evidence: bool,
) -> List[str]:
    """
    Mechanism 2 + 4 — Mandatory evidence and source validation.
    Returns a list of warning strings (empty = OK).
    """
    warnings: List[str] = []

    if claim.status in ("supported",) and not claim.sources and require_evidence:
        warnings.append(
            f"UNSUPPORTED CLAIM: '{claim.claim[:80]}' marked 'supported' but has no sources."
        )
        return warnings

    for src in claim.sources:
        key = (src.document, src.page)
        if key not in valid_citations:
            warnings.append(
                f"INVALID CITATION: {src.document} p.{src.page} "
                f"not found in retrieved evidence."
            )

    return warnings


def validate_reasoning(
    result: ReasoningResult,
    retrieved: List[RetrievedChunk],
    pages: List[PageRecord],
) -> ValidationResult:
    """
    Full validation pass over the ReasoningResult.

    Returns a ValidationResult with passed=True only if:
    - All 'supported' claims have at least one source
    - All cited (document, page) pairs exist in retrieved chunks
    - There is at least one supported finding
    """
    valid_citations = _build_valid_citations(retrieved, pages)
    all_warnings: List[str] = []
    invalid_citation_msgs: List[str] = []
    unsupported_count = 0

    # Check supported findings (must have evidence)
    for claim in result.supported_findings:
        ws = _validate_claim(claim, valid_citations, require_evidence=True)
        for w in ws:
            if "UNSUPPORTED" in w:
                unsupported_count += 1
            else:
                invalid_citation_msgs.append(w)
        all_warnings.extend(ws)

    # Check inferences (evidence optional but citations must be valid if present)
    for claim in result.inferences:
        ws = _validate_claim(claim, valid_citations, require_evidence=False)
        all_warnings.extend(ws)
        invalid_citation_msgs.extend([w for w in ws if "INVALID" in w])

    # Must have at least one supported finding to pass
    missing_evidence = len(result.supported_findings) == 0

    passed = (
        unsupported_count == 0
        and len(invalid_citation_msgs) == 0
        and not missing_evidence
    )

    failure_reason = None
    if not passed:
        parts = []
        if missing_evidence:
            parts.append("No supported findings — evidence insufficient.")
        if unsupported_count:
            parts.append(f"{unsupported_count} unsupported claim(s).")
        if invalid_citation_msgs:
            parts.append(f"{len(invalid_citation_msgs)} invalid citation(s).")
        failure_reason = " ".join(parts)

    return ValidationResult(
        passed=passed,
        unsupported_count=unsupported_count,
        invalid_citations=invalid_citation_msgs,
        missing_evidence=missing_evidence,
        warnings=all_warnings,
        failure_reason=failure_reason,
    )
