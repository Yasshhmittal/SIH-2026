"""
core/health.py — Startup preflight checks for NEBULA (Phase 9 hardening).

Before the UI enables the agent, verify that the local, offline dependencies
are actually available:
  - Ollama server reachable at localhost:11434
  - The three required models are pulled (qwen2.5:7b, qwen2.5vl:7b, bge-m3)

These checks use a SHORT timeout so the UI fails fast with a clear message
instead of hanging deep inside the pipeline. No cloud calls are made.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

# Required Ollama models (matched as substrings so ":latest" tags still count).
REQUIRED_MODELS = ["qwen2.5:7b", "qwen2.5vl:7b", "bge-m3"]

# Fast fail: the server is local, so a few seconds is plenty.
HEALTH_TIMEOUT = float(os.getenv("OLLAMA_HEALTH_TIMEOUT", "5"))


@dataclass
class Preflight:
    """Result of the startup dependency check."""
    ollama_up: bool = False
    models_present: List[str] = field(default_factory=list)
    models_missing: List[str] = field(default_factory=list)
    message: str = ""

    @property
    def ready(self) -> bool:
        """True only when Ollama is up and every required model is present."""
        return self.ollama_up and not self.models_missing


def check_ollama(required: List[str] | None = None) -> Preflight:
    """
    Probe the local Ollama server and installed models.

    Returns a Preflight result. Never raises — a failed probe is reported
    as ollama_up=False with a human-readable message.
    """
    required = required or REQUIRED_MODELS
    result = Preflight()

    try:
        import ollama

        # Short-timeout client so a dead server fails in seconds, not minutes.
        client = ollama.Client(timeout=HEALTH_TIMEOUT)
        listing = client.list()
        installed = [m.model for m in listing.models]
        result.ollama_up = True

        for req in required:
            if any(req in name for name in installed):
                result.models_present.append(req)
            else:
                result.models_missing.append(req)

        if result.models_missing:
            result.message = (
                "Ollama is running but these models are not pulled: "
                + ", ".join(result.models_missing)
                + ". Run: "
                + " && ".join(f"ollama pull {m}" for m in result.models_missing)
            )
        else:
            result.message = "All local models available. Running fully offline."
    except Exception as exc:  # connection refused, timeout, etc.
        result.ollama_up = False
        result.message = (
            f"Ollama is not reachable at localhost:11434 ({exc}). "
            "Start it with: ollama serve"
        )

    return result
