"""
server/events.py — Translate NEBULA's human-readable pipeline log strings into
the structured event schema the PRAHARÍ frontend expects.

The backend agent (core/agent.py) emits emoji-prefixed strings such as:
    "⚙️  CLASSIFY — Analysing document type..."
    "✅ CLASSIFY — Inspection Review | 3 pages | Vision: False"
    "❌ OCR failed: ..."
    "⏭️  VISION — No visual content detected; step skipped"
    "🏁 Agent pipeline complete."

The frontend timeline (AgentTimeline.jsx) renders events of the form:
    { type, step, status, message, timestamp, data: {...} }
where status ∈ {started, completed, failed, error} and matching `step` values
let a `completed` event resolve the earlier `started` spinner for that step.

This module is the single place that knows how to map one to the other.
"""
from __future__ import annotations

import datetime
from typing import Optional

# Keywords that identify a pipeline step, in priority order. Both the "started"
# and the "completed" log line for a step contain the same keyword, so they map
# to the same `step` token and the frontend pairs them.
_STEP_KEYWORDS = [
    ("CLASSIFY", "classify"),
    ("OCR", "ocr"),
    ("VISION", "vision"),
    ("RETRIEVAL", "retrieval"),
    ("REASONING", "reasoning"),
    ("VALIDATION", "validation"),
    ("DOCX", "docx"),
]

# Leading emoji → status. Anything not listed is treated as a "started" step.
_COMPLETED_PREFIXES = ("✅",)
_FAILED_PREFIXES = ("❌", "🚫")
_WARN_PREFIXES = ("⚠️",)
_SKIPPED_PREFIXES = ("⏭️",)
_DONE_PREFIXES = ("🏁",)

# Emoji we strip from the front of a message for clean display (the frontend
# renders its own status icons).
_STRIP_EMOJI = [
    "✅", "❌", "🚫", "⚠️", "⏭️", "🏁",
    "⚙️", "📄", "🔍", "📚", "🔎", "🧠", "✔️", "📝",
]


def now_iso() -> str:
    """Timestamp in ISO format (frontend parses with new Date())."""
    return datetime.datetime.now().isoformat()


def _clean(message: str) -> str:
    msg = message.strip()
    for emoji in _STRIP_EMOJI:
        if msg.startswith(emoji):
            msg = msg[len(emoji):].strip()
            break
    return msg


def _status_for(message: str) -> str:
    msg = message.strip()
    if msg.startswith(_DONE_PREFIXES):
        return "completed"
    if msg.startswith(_COMPLETED_PREFIXES):
        return "completed"
    if msg.startswith(_FAILED_PREFIXES):
        return "failed"
    if msg.startswith(_WARN_PREFIXES):
        return "completed"  # non-fatal warning; shown as done
    if msg.startswith(_SKIPPED_PREFIXES):
        return "completed"  # skipped step; shown as done
    return "started"


def _step_for(message: str) -> str:
    upper = message.upper()
    for keyword, token in _STEP_KEYWORDS:
        if keyword in upper:
            return token
    if message.strip().startswith(_DONE_PREFIXES):
        return "pipeline"
    return "info"


def make(
    status: str,
    step: str,
    message: str,
    data: Optional[dict] = None,
    type_: str = "agent",
) -> dict:
    """Build a structured event dict for the frontend."""
    return {
        "type": type_,
        "step": step,
        "status": status,
        "message": message,
        "timestamp": now_iso(),
        "data": data or {},
    }


def translate(raw_message: str, data: Optional[dict] = None) -> dict:
    """Convert one NEBULA log string into a structured frontend event."""
    return make(
        status=_status_for(raw_message),
        step=_step_for(raw_message),
        message=_clean(raw_message),
        data=data,
    )
