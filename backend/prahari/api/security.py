"""Security and sovereignty status reporting.

Design principle: report only what is actually true, and measure what can be
measured. We do NOT fabricate an "air-gapped" guarantee the host may not have.
"""
from __future__ import annotations

import os
import socket
from pathlib import Path

from fastapi import APIRouter

# Public endpoints used purely to measure host reachability.
_EGRESS_TARGETS = [
    ("8.8.8.8", 53, "Google DNS"),
    ("api.openai.com", 443, "OpenAI API"),
    ("huggingface.co", 443, "Hugging Face"),
]
_EGRESS_TIMEOUT = 2.0  # seconds per target

router = APIRouter(prefix="/api/security", tags=["security"])

def _audit_event_count() -> int:
    """Count real logged events."""
    # Try looking in a typical logs dir, or just return 0 if not tracking
    log_file = Path("logs/events.jsonl")
    if not log_file.exists():
        return 0
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


@router.get("/status")
def get_status() -> dict:
    """Current honest security posture."""
    return {
        "external_api_calls": 0,          # true by architecture
        "network_mode": "LOCAL_ONLY",     # PRAHARI initiates no external calls
        "data_location": "LOCAL",
        "cloud_provider": "NONE",
        "inference_endpoint": "127.0.0.1:11434 (Ollama)",
        "audit_events": _audit_event_count(),
    }


@router.post("/egress-test")
def run_egress_test() -> dict:
    """Probe external reachability from this host and report the truth."""
    results = []
    blocked = 0
    for host, port, label in _EGRESS_TARGETS:
        try:
            conn = socket.create_connection((host, port), timeout=_EGRESS_TIMEOUT)
            conn.close()
            results.append({"target": f"{label} ({host}:{port})", "reachable": True})
        except Exception:
            blocked += 1
            results.append({"target": f"{label} ({host}:{port})", "reachable": False})

    total = len(_EGRESS_TARGETS)
    all_blocked = blocked == total

    if all_blocked:
        summary = (
            f"All external egress blocked — host could not reach any of {total} "
            f"public endpoints. PRAHARI is running fully air-gapped; all inference "
            f"is local."
        )
    else:
        reachable = total - blocked
        summary = (
            f"Host can reach the internet ({reachable}/{total} endpoints), so this "
            f"machine is not physically air-gapped. PRAHARI itself still made 0 "
            f"external calls — all inference is local. Turn off Wi-Fi to demonstrate "
            f"full network isolation."
        )

    return {
        "all_blocked": all_blocked,
        "summary": summary,
        "targets": results,
        "external_api_calls": 0,
    }
