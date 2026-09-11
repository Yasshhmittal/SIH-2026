"""Tool registry and policy gate.

Deny-by-default: a tool that is not registered cannot be called, and a tool
whose declared capabilities are not granted to the run is refused before its
handler is reached. There is deliberately no shell tool and no network tool —
see docs/context.md §7.1. That absence is what bounds the blast radius of a
prompt injection.

Every call produces an AuditRecord whether it succeeds or fails.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from ..agent.schemas import Observation


class ToolHandler(Protocol):
    def __call__(self, ctx: "ToolContext", **kwargs: Any) -> Observation: ...


@dataclass
class ToolContext:
    """Everything a tool is allowed to know about the run it serves."""

    run_id: str
    org_id: str
    workspace: Any                      # pathlib.Path, jailed
    emit: Callable[[str, dict[str, Any]], None]
    scratch: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_schema: dict[str, Any]
    capabilities: frozenset[str]
    handler: ToolHandler
    returns: str = ""
    # Tools the planner should not see (internal/meta) stay hidden.
    planner_visible: bool = True


class ToolError(RuntimeError):
    pass


class PolicyViolation(ToolError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"duplicate tool: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def names(self, planner_visible_only: bool = False) -> list[str]:
        return sorted(
            name for name, spec in self._tools.items()
            if not planner_visible_only or spec.planner_visible
        )

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def describe_for_planner(self) -> str:
        """Compact tool catalogue injected into the planning prompt.

        Kept terse on purpose: a 1.5B model given three paragraphs per tool
        starts copying the prose into its arguments.
        """
        lines: list[str] = []
        for spec in sorted(self._tools.values(), key=lambda s: s.name):
            if not spec.planner_visible:
                continue
            props = (spec.args_schema or {}).get("properties", {})
            required = set((spec.args_schema or {}).get("required", []))
            arg_bits = []
            for arg, meta in props.items():
                mark = "" if arg in required else "?"
                arg_bits.append(f"{arg}{mark}:{meta.get('type', 'any')}")
            lines.append(f"- {spec.name}({', '.join(arg_bits)}) — {spec.description}")
        return "\n".join(lines)

    # -- invocation --------------------------------------------------------

    def validate_call(self, name: str, args: dict[str, Any]) -> tuple[bool, str]:
        """Check a planned call *before* it runs. Cheap, and catches the
        common 1.5B failure mode of inventing a tool or omitting an arg."""
        spec = self.get(name)
        if spec is None:
            return False, f"unknown tool '{name}'"

        required = set((spec.args_schema or {}).get("required", []))
        missing = required - set(args or {})
        if missing:
            return False, f"missing required args: {', '.join(sorted(missing))}"
        return True, ""

    def invoke(
        self,
        name: str,
        ctx: ToolContext,
        args: dict[str, Any],
        granted: frozenset[str],
    ) -> Observation:
        spec = self.get(name)
        if spec is None:
            return Observation(ok=False, error=f"unknown tool '{name}'",
                               summary="tool not found")

        ungranted = spec.capabilities - granted
        if ungranted:
            return Observation(
                ok=False,
                error=f"policy denied capabilities: {', '.join(sorted(ungranted))}",
                summary="blocked by policy",
            )

        ok, reason = self.validate_call(name, args)
        if not ok:
            return Observation(
                ok=False,
                error=reason,
                summary="invalid arguments",
                data={"schema": spec.args_schema},
            )

        started = time.perf_counter()
        try:
            obs = spec.handler(ctx, **(args or {}))
        except TypeError as exc:
            obs = Observation(ok=False, error=f"bad arguments: {exc}",
                              summary="invalid arguments")
        except Exception as exc:  # a failing tool must not kill the run
            obs = Observation(ok=False, error=f"{type(exc).__name__}: {exc}",
                              summary="tool raised")
        obs.duration_ms = int((time.perf_counter() - started) * 1000)
        return obs


registry = ToolRegistry()


# Capability vocabulary. Grants are per-run and come from the org's policy.yaml.
CAP_KB_READ = "kb.read"
CAP_FS_READ = "fs.read"
CAP_FS_WRITE = "fs.write"
CAP_EXEC_SANDBOX = "exec.sandbox"
CAP_VISION = "vision"
CAP_RENDER = "render"
CAP_COMPUTE = "compute"

# The default grant for an interactive run. Note what is absent: there is no
# network capability anywhere in this vocabulary.
DEFAULT_GRANTS = frozenset({
    CAP_KB_READ, CAP_FS_READ, CAP_FS_WRITE,
    CAP_EXEC_SANDBOX, CAP_VISION, CAP_RENDER, CAP_COMPUTE,
})
