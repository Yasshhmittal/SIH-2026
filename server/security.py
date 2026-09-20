"""
server/security.py — Honest security / sovereignty status for the PRAHARÍ panel.

Design principle: report only what is actually true, and measure what can be
measured. We do NOT fabricate an "air-gapped" guarantee the host may not have.

  - external_api_calls: 0     → TRUE by architecture. NEBULA only ever talks to
                                the local Ollama server (127.0.0.1:11434) and the
                                local filesystem. There is no cloud client, no API
                                key, anywhere in the codebase.
  - audit_events:             → real line count of the append-only event log
                                (logs/events.jsonl).
  - network_mode: LOCAL_ONLY  → describes NEBULA's own behaviour (it initiates no
                                external connections), not a claim about the host.

The egress test genuinely attempts outbound TCP connections to public endpoints
and reports the result truthfully:
  - Wi-Fi off / air-gapped host → all connections fail → "all egress blocked".
  - Online host                 → connections succeed → we say so plainly, and
                                   note that NEBULA still made 0 external calls.
"""
from __future__ import annotations

import os
import socket
from pathlib import Path

LOGS_DIR = Path(os.getenv("LOGS_DIR", "./logs"))

# Public endpoints used purely to measure host reachability. NEBULA never calls
# these during normal operation — they exist only for this on-demand test.
_EGRESS_TARGETS = [
    ("8.8.8.8", 53, "Google DNS"),
    ("api.openai.com", 443, "OpenAI API"),
    ("huggingface.co", 443, "Hugging Face"),
]
_EGRESS_TIMEOUT = 2.0  # seconds per target


def _audit_event_count() -> int:
    """Count real logged events (lines in logs/events.jsonl)."""
    log_file = LOGS_DIR / "events.jsonl"
    if not log_file.exists():
        return 0
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def get_status() -> dict:
    """Current honest security posture for the right-panel Security block."""
    return {
        "external_api_calls": 0,          # true by architecture
        "network_mode": "LOCAL_ONLY",     # NEBULA initiates no external calls
        "data_location": "LOCAL",
        "cloud_provider": "NONE",
        "inference_endpoint": "127.0.0.1:11434 (Ollama)",
        "audit_events": _audit_event_count(),
    }


def run_egress_test() -> dict:
    """
    Actually probe external reachability from this host and report the truth.

    Returns a dict the frontend renders:
        { all_blocked: bool, summary: str, targets: [...] }
    """
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
            f"public endpoints. NEBULA is running fully air-gapped; all inference "
            f"is local (Ollama @127.0.0.1)."
        )
    else:
        reachable = total - blocked
        summary = (
            f"Host can reach the internet ({reachable}/{total} endpoints), so this "
            f"machine is not physically air-gapped. NEBULA itself still made 0 "
            f"external calls — all inference is local (Ollama @127.0.0.1). Turn off "
            f"Wi-Fi to demonstrate full network isolation."
        )

    return {
        "all_blocked": all_blocked,
        "summary": summary,
        "targets": results,
        "external_api_calls": 0,
    }
