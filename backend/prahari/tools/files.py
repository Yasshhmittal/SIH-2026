"""Filesystem tools, jailed to the org workspace.

Path confinement is enforced by resolving and then checking containment — not
by string prefix matching, which `..` defeats. A tool that escapes its jail is
an exfiltration primitive, so this is checked on every call.
"""

from __future__ import annotations

from pathlib import Path

from ..agent.schemas import Observation
from .base import CAP_FS_READ, CAP_FS_WRITE, ToolContext, ToolSpec, registry

MAX_READ_BYTES = 512_000


def _resolve_in_jail(ctx: ToolContext, relative: str) -> Path | None:
    """Resolve `relative` inside the workspace, or None if it escapes."""
    root = Path(ctx.workspace).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def fs_read(ctx: ToolContext, *, path: str) -> Observation:
    target = _resolve_in_jail(ctx, path)
    if target is None:
        return Observation(ok=False, summary="path escapes workspace",
                           error=f"refused: '{path}' resolves outside the jail")
    if not target.exists():
        return Observation(ok=False, summary="not found", error=f"no such file: {path}")
    if target.stat().st_size > MAX_READ_BYTES:
        return Observation(ok=False, summary="file too large",
                           error=f"{target.stat().st_size} bytes exceeds {MAX_READ_BYTES}")

    text = target.read_text(encoding="utf-8", errors="replace")
    return Observation(
        ok=True,
        summary=f"read {len(text)} chars from {path}",
        data={"path": path, "content": text, "bytes": target.stat().st_size},
    )


def fs_write(ctx: ToolContext, *, path: str, content: str) -> Observation:
    target = _resolve_in_jail(ctx, path)
    if target is None:
        return Observation(ok=False, summary="path escapes workspace",
                           error=f"refused: '{path}' resolves outside the jail")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return Observation(
        ok=True,
        summary=f"wrote {len(content)} chars to {path}",
        data={"path": path, "bytes": len(content.encode("utf-8"))},
    )


registry.register(
    ToolSpec(
        name="fs.read",
        description="Read a UTF-8 text file from the run workspace.",
        args_schema={
            "type": "object",
            "properties": {"path": {"type": "string",
                                    "description": "Path relative to the workspace"}},
            "required": ["path"],
        },
        capabilities=frozenset({CAP_FS_READ}),
        handler=fs_read,
        returns="file content as text",
    )
)

registry.register(
    ToolSpec(
        name="fs.write",
        description="Write a UTF-8 text file into the run workspace.",
        args_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to the workspace"},
                "content": {"type": "string", "description": "Text to write"},
            },
            "required": ["path", "content"],
        },
        capabilities=frozenset({CAP_FS_WRITE}),
        handler=fs_write,
        returns="path and byte count written",
    )
)
