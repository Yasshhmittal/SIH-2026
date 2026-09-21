"""Sandbox tool for executing Python code in an isolated environment."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from ..agent.schemas import Observation
from .base import CAP_EXEC_SANDBOX, ToolContext, ToolSpec, registry


def code_run(ctx: ToolContext, *, code: str, tests: str | None = None) -> Observation:
    """Run Python code in a network-isolated Docker container."""
    workspace = Path(ctx.workspace)
    scratch = workspace / "sandbox_scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    
    script_path = scratch / "script.py"
    
    full_code = code
    if tests:
        full_code += "\n\n" + tests
        
    script_path.write_text(full_code, encoding="utf-8")
    
    cmd = [
        "docker", "run", "--rm",
        "--network", "none",
        "--cpus", "1",
        "--memory", "512m",
        "-v", f"{scratch.resolve()}:/sandbox",
        "-w", "/sandbox",
        "python:3.12-alpine",
        "python", "script.py"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return Observation(
            ok=result.returncode == 0,
            summary=f"Code execution finished with code {result.returncode}",
            data={
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "code_chars": len(code),
                "has_tests": bool(tests),
            }
        )
    except subprocess.TimeoutExpired as exc:
        return Observation(
            ok=False,
            summary="Code execution timed out",
            data={
                "stdout": exc.stdout.decode() if exc.stdout else "",
                "stderr": exc.stderr.decode() if exc.stderr else "Timed out after 15s",
                "exit_code": -1,
            }
        )
    except Exception as exc:
        return Observation(
            ok=False,
            summary=f"Failed to start sandbox: {exc}",
            data={"error": str(exc)}
        )

registry.register(
    ToolSpec(
        name="code.run",
        description="Run Python in an isolated sandbox with no network. Returns output.",
        args_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source to execute"},
                "tests": {"type": "string", "description": "Optional pytest source"},
            },
            "required": ["code"],
        },
        capabilities=frozenset({CAP_EXEC_SANDBOX}),
        handler=code_run,
        returns="stdout, stderr, exit code",
    )
)
