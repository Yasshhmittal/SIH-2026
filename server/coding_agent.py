"""
server/coding_agent.py — Real local Coding Agent for the PRAHARÍ "Coding" workflow.

Loop: Qwen2.5-7B generates a self-contained Python script → the script is run in
a local subprocess with a wall-clock timeout → on failure the traceback is fed
back to the model, which self-corrects (bounded to MAX_ITERS attempts).

Honesty:
  - This is a bounded local subprocess with a timeout, NOT a hardened sandbox.
    Generated code runs on this machine with the same permissions as the server.
  - The model is instructed to use only the standard library and to include
    assert-based self-tests, so a return code of 0 with printed PASS lines is a
    genuine signal that the produced code ran and its own checks passed.
  - Uses the existing QwenText Ollama wrapper and evicts the model (keep_alive=0)
    when done — the M4 memory-safety contract is preserved.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple

from server.events import make

MAX_ITERS = 3
RUN_TIMEOUT = 15          # seconds per execution
OUTPUT_CAP = 4000         # chars of stdout/stderr surfaced to the UI

_CODING_SYSTEM = (
    "You are an expert Python 3 developer. Output ONLY a single complete, "
    "self-contained Python script and nothing else — no markdown code fences, "
    "no explanation before or after. The script MUST end with an "
    "`if __name__ == \"__main__\":` block that exercises the solution with a few "
    "assert-based tests and prints a line 'PASS: <description>' for each passing "
    "test. Use only the Python standard library."
)


def _strip_fences(text: str) -> str:
    """Remove ```python ... ``` fences if the model added them despite instructions."""
    t = text.strip()
    fence = re.match(r"^```(?:python)?\s*\n(.*?)\n```\s*$", t, flags=re.DOTALL)
    if fence:
        return fence.group(1).strip()
    # Also handle a stray leading/trailing fence line
    t = re.sub(r"^```(?:python)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _generate_code(qwen, task: str, last_error: Optional[str]) -> str:
    if last_error:
        user = (
            f"Task:\n{task}\n\n"
            f"The previous version of your script failed when executed:\n"
            f"```\n{last_error[:2000]}\n```\n"
            f"Return the FULL corrected script (not a diff)."
        )
    else:
        user = f"Task:\n{task}"
    raw = qwen.complete(user, system=_CODING_SYSTEM, max_tokens=1200)
    return _strip_fences(raw)


def _run_code(code: str) -> Tuple[int, str, str]:
    """Run code in a temp dir subprocess with a timeout. Returns (rc, stdout, stderr)."""
    with tempfile.TemporaryDirectory(prefix="nebula_code_") as tmpdir:
        script = Path(tmpdir) / "solution.py"
        script.write_text(code, encoding="utf-8")
        # Minimal environment; run from the temp dir so any files land there.
        env = {"PATH": os.environ.get("PATH", ""), "HOME": tmpdir}
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT,
                cwd=tmpdir,
                env=env,
            )
            return proc.returncode, proc.stdout[:OUTPUT_CAP], proc.stderr[:OUTPUT_CAP]
        except subprocess.TimeoutExpired:
            return -1, "", f"Execution timed out after {RUN_TIMEOUT}s (possible infinite loop)."
        except Exception as exc:  # pragma: no cover - defensive
            return -1, "", f"Failed to execute generated code: {exc}"


def run_coding_agent(task: str, emit: Callable[[dict], None]) -> None:
    """
    Execute the coding workflow, emitting frontend events via `emit`.
    Blocking; intended to run in a background thread.
    """
    emit(make("started", "profile", "Coding Agent initialised.", {
        "profile": {
            "name": "Coding Agent",
            "model": "Qwen2.5-7B",
            "mode": "Generate → Test → Self-Correct",
        }
    }))
    emit(make("started", "plan", "Planning approach…", {
        "plan": [
            "Generate a self-contained Python solution with Qwen2.5-7B",
            f"Run it in a local subprocess (timeout {RUN_TIMEOUT}s)",
            f"On failure, feed the error back and self-correct (≤{MAX_ITERS} attempts)",
        ]
    }))
    emit(make("completed", "plan", "Plan ready — generating and testing code.", {}))

    from models.qwen_text import QwenText

    qwen = QwenText()
    code = ""
    last_error: Optional[str] = None
    final_output = ""
    success = False
    attempts = 0

    try:
        for i in range(1, MAX_ITERS + 1):
            attempts = i
            gen_step = f"generate-{i}"
            if i == 1:
                emit(make("started", gen_step, "Generating Python solution (attempt 1)…", {}))
                code = _generate_code(qwen, task, None)
                emit(make("completed", gen_step, "Generated candidate solution (attempt 1).", {"code": code}))
            else:
                emit(make("started", gen_step, f"Self-correcting from previous error (attempt {i})…", {}))
                code = _generate_code(qwen, task, last_error)
                emit(make("completed", gen_step, f"Produced revised solution (attempt {i}).", {"corrected_code": code}))

            exec_step = f"execute-{i}"
            emit(make("started", exec_step, f"Running generated code (attempt {i})…", {}))
            rc, out, err = _run_code(code)

            if rc == 0:
                final_output = out or "(no stdout)"
                success = True
                emit(make("completed", exec_step, f"Code executed successfully (attempt {i}).", {"output": final_output}))
                break
            else:
                last_error = err or f"Non-zero exit code ({rc}) with no stderr."
                emit(make("failed", exec_step, f"Execution failed (attempt {i}).", {"error": last_error}))
    except Exception as exc:
        last_error = str(exc)
        emit(make("failed", "coding", f"Coding agent error: {exc}", {"error": last_error}))
    finally:
        qwen.unload()  # release VRAM (keep_alive=0)

    if success:
        emit(make("completed", "complete", f"Coding task complete — tests passed in {attempts} attempt(s).", {
            "code": code,
            "output": final_output,
            "passed": True,
            "iterations": attempts,
        }))
    else:
        emit(make("completed", "complete",
                  f"Coding task did not reach a passing run after {attempts} attempt(s). Latest code and error shown above.", {
                      "code": code,
                      "error": last_error or "unknown error",
                      "passed": False,
                      "iterations": attempts,
                  }))
