"""
models/qwen_text.py — Qwen2.5-7B-Instruct wrapper for NEBULA (Ollama backend).

Responsibilities (from plan §4.1):
  - Task interpretation and classification
  - Reasoning over retrieved SOP evidence
  - Structured grounded JSON output
  - DOCX content generation

NOT used for: OCR, factual invention, or retrieval.
Uses Ollama API at localhost:11434 — fully local, no cloud.
"""

from __future__ import annotations

import json
import os
import re
from typing import List

import ollama

from core.schemas import (
    EvidenceSource,
    GroundedClaim,
    PageRecord,
    ReasoningResult,
    RetrievedChunk,
)

MODEL_NAME = os.getenv("QWEN_TEXT_MODEL", "qwen2.5:7b")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
MAX_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "1024"))
# Generous timeout: covers cold model load + generation on Apple M4.
# Env-configurable so slow machines can raise it. A hung call fails cleanly
# instead of freezing the demo.
CHAT_TIMEOUT = float(os.getenv("OLLAMA_CHAT_TIMEOUT", "300"))


def _client() -> "ollama.Client":
    """Ollama client with an explicit timeout (fully local, no cloud)."""
    return ollama.Client(timeout=CHAT_TIMEOUT)


# ── Prompt construction ───────────────────────────────────────────────────────

def _build_reasoning_prompt(
    task: str,
    pages: List[PageRecord],
    retrieved: List[RetrievedChunk],
) -> str:
    """
    Construct the grounding prompt exactly as specified in plan §5.5.
    Only retrieved evidence is passed — no model memory for facts.
    """
    # Observed document facts (from OCR/native text)
    observed_facts = []
    for p in pages[:5]:  # limit context
        obs = f"[{p.document} · Page {p.page} · {p.source_type}]\n{p.text[:800]}"
        observed_facts.append(obs)

    # Visual observations
    visual_obs = []
    for p in pages:
        for vo in p.visual_observations:
            visual_obs.append(
                f"- Page {vo.page}: {vo.text} (confidence: {vo.confidence})"
            )

    # Retrieved SOP evidence
    sop_evidence = []
    for rc in retrieved:
        sop_evidence.append(
            f"[{rc.chunk.document} · Page {rc.chunk.page} · score={rc.score:.3f}]\n{rc.chunk.text}"
        )

    prompt = f"""You are a local AI assistant performing industrial document analysis.
You must reason ONLY from the evidence provided below. Do not use general knowledge for factual industrial claims.

USER REQUEST:
{task}

OBSERVED DOCUMENT FACTS:
{chr(10).join(observed_facts) if observed_facts else "None extracted."}

VISUAL OBSERVATIONS:
{chr(10).join(visual_obs) if visual_obs else "None."}

RETRIEVED SOP EVIDENCE:
{chr(10).join(sop_evidence) if sop_evidence else "No SOP evidence retrieved."}

RULES:
1. Use ONLY the evidence provided above.
2. Do NOT use model memory for factual industrial claims.
3. Every important conclusion must cite source document and page number.
4. Separate supported facts, inference, and uncertainty clearly.
5. If evidence is insufficient, state: "Cannot determine from the provided evidence."
6. Respond ONLY with valid JSON matching the schema below.

OUTPUT JSON SCHEMA:
{{
  "task_class": "Inspection Review",
  "supported_findings": [
    {{
      "claim": "...",
      "status": "supported",
      "sources": [{{"document": "...", "page": N, "evidence": "..."}}]
    }}
  ],
  "inferences": [
    {{
      "claim": "...",
      "status": "inference",
      "sources": [{{"document": "...", "page": N, "evidence": "..."}}]
    }}
  ],
  "uncertainties": [
    {{
      "claim": "Cannot determine X from the provided evidence.",
      "status": "uncertain",
      "sources": []
    }}
  ],
  "recommended_action": "..."
}}"""
    return prompt


# ── Model wrapper ─────────────────────────────────────────────────────────────

class QwenText:
    """Qwen2.5-7B wrapper using Ollama API."""

    def _generate(self, prompt: str) -> str:
        """Call Ollama generate endpoint."""
        response = _client().chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise industrial AI assistant. Always respond with valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS,
            },
        )
        return response["message"]["content"].strip()

    def complete(self, user_prompt: str, system: str | None = None,
                 max_tokens: int | None = None) -> str:
        """
        Free-form completion (NOT JSON-constrained).

        Used by the coding agent, which needs raw code output rather than the
        grounded-JSON schema that `reason()` enforces. Kept separate from
        `reason()` so the working reasoning path is untouched.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_prompt})
        response = _client().chat(
            model=MODEL_NAME,
            messages=messages,
            options={
                "temperature": TEMPERATURE,
                "num_predict": max_tokens or MAX_TOKENS,
            },
        )
        return response["message"]["content"].strip()

    def unload(self) -> None:
        """Explicitly unload from Ollama to free memory."""
        try:
            _client().generate(model=MODEL_NAME, prompt='', keep_alive=0)
        except Exception:
            pass

    def reason(
        self,
        task: str,
        pages: List[PageRecord],
        retrieved: List[RetrievedChunk],
    ) -> ReasoningResult:
        """Run grounded reasoning and return a structured ReasoningResult."""
        prompt = _build_reasoning_prompt(task, pages, retrieved)
        raw = self._generate(prompt)

        # Parse JSON (with fallback)
        try:
            # Strip markdown code fences if present
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            data = json.loads(clean)
        except json.JSONDecodeError:
            # Graceful fallback — wrap raw text as an uncertain claim
            return ReasoningResult(
                task_class="Unknown",
                uncertainties=[
                    GroundedClaim(
                        claim="Model response could not be parsed as JSON. Raw output stored for review.",
                        status="uncertain",
                    )
                ],
                recommended_action="Manual review of raw model output required.",
                raw_json=raw,
            )

        def parse_claims(items: list, status: str) -> List[GroundedClaim]:
            claims = []
            for item in (items or []):
                sources = [
                    EvidenceSource(
                        document=s.get("document", ""),
                        page=s.get("page", 0),
                        evidence=s.get("evidence", ""),
                    )
                    for s in item.get("sources", [])
                ]
                claims.append(GroundedClaim(
                    claim=item.get("claim", ""),
                    status=item.get("status", status),
                    sources=sources,
                ))
            return claims

        return ReasoningResult(
            task_class=data.get("task_class", "Inspection Review"),
            supported_findings=parse_claims(data.get("supported_findings", []), "supported"),
            inferences=parse_claims(data.get("inferences", []), "inference"),
            uncertainties=parse_claims(data.get("uncertainties", []), "uncertain"),
            recommended_action=data.get("recommended_action", ""),
            raw_json=raw,
        )
