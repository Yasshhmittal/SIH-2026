"""Console client for a PRAHARI run — streams the agent timeline as SSE.

Stands in for the browser until the Next.js console lands, and doubles as the
smoke test for the whole loop:

    python scripts/run_task.py "draft an approval note for elbow E-14"
"""

from __future__ import annotations

import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8077"


def fmt_router_table(payload: dict) -> list[str]:
    lines = [f"    ROUTER · {payload.get('label', '')}"]
    for cand in payload.get("candidates", []):
        if cand["rejected"]:
            lines.append(f"      ✗ {cand['model_id']:<22} {cand['reason']}")
        else:
            mark = "→" if cand["model_id"] == payload.get("chosen") else " "
            resident = " [resident]" if cand.get("resident") else ""
            lines.append(
                f"      {mark} {cand['model_id']:<22} score={cand['score']:.3f}"
                f"  mem={cand['mem_mb']}MB{resident}"
            )
    if payload.get("explanation"):
        lines.append(f"      why: {payload['explanation']}")
    return lines


def main() -> int:
    prompt = " ".join(sys.argv[1:]) or (
        "Draft an approval note for the thickness deficiency found at Elbow "
        "E-14 on line 8-P-1204. Nominal wall was 8.0 mm, the latest UT reading "
        "is 5.9 mm, minimum allowed is 6.4 mm, and the line has been in "
        "service 7 years. Show the corrosion rate calculation."
    )

    print(f"\n\033[1mPROMPT\033[0m  {prompt}\n")

    started = time.time()
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        run_id = client.post("/api/runs", json={"prompt": prompt}).json()["run_id"]
        print(f"run_id  {run_id}\n" + "─" * 78)

    with httpx.Client(base_url=BASE, timeout=None) as client:
        with client.stream("GET", f"/api/runs/{run_id}/events") as response:
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line[5:].strip())
                kind, payload = event["type"], event["payload"]
                elapsed = time.time() - started

                if kind == "run.started":
                    print(f"[{elapsed:6.1f}s] RUN START  profile={payload['profile']}")

                elif kind == "stage.started":
                    print(f"[{elapsed:6.1f}s] {payload['stage'].upper()} ...")

                elif kind == "router.decision":
                    for line_out in fmt_router_table(payload):
                        print(f"[{elapsed:6.1f}s] {line_out}")

                elif kind == "router.swap":
                    evicted = ", ".join(payload["evicted"]) or "nothing"
                    print(f"[{elapsed:6.1f}s]     SWAP loaded {payload['loaded']} "
                          f"in {payload['load_s']}s (evicted: {evicted})")

                elif kind == "stage.completed" and payload["stage"] == "classify":
                    task = payload["task"]
                    print(f"[{elapsed:6.1f}s] CLASSIFIED {task['kind']} "
                          f"· deliverable={task['deliverable']} "
                          f"· {payload['tokens_per_second']} tok/s")
                    print(f"           needs: vision={task['needs_vision']} "
                          f"code={task['needs_code']} retrieval={task['needs_retrieval']} "
                          f"calc={task['needs_calculation']}")

                elif kind == "classify.reconciled":
                    for fix in payload["corrections"]:
                        print(f"[{elapsed:6.1f}s] \033[33mRECONCILED\033[0m "
                              f"{fix['field']}: {fix['from']} -> {fix['to']} "
                              f"(evidence: {fix['evidence']!r})")

                elif kind == "plan.created":
                    print(f"[{elapsed:6.1f}s] PLAN ({payload['tokens_per_second']} tok/s)"
                          f"  goal: {payload['goal'][:70]}")
                    for step in payload["steps"]:
                        print(f"           {step['id']}. {step['tool']:<16} {step['why'][:52]}")

                elif kind == "plan.repaired":
                    for drop in payload["dropped"]:
                        print(f"[{elapsed:6.1f}s] PLAN REPAIR dropped "
                              f"{drop['tool']}: {drop['reason']}")

                elif kind == "step.started":
                    print(f"[{elapsed:6.1f}s]   ▶ step {payload['id']} {payload['tool']}")

                elif kind == "step.repaired":
                    print(f"[{elapsed:6.1f}s] \033[33m  ↻ REPAIRED\033[0m step "
                          f"{payload['id']} ({payload['tool']}) — fixed: "
                          f"{payload['fixed'][:60]}")
                    print(f"           args {payload['before']} -> {payload['after']}")
                    print(f"           replans used: {payload['replans_used']}")

                elif kind == "step.repair_failed":
                    print(f"[{elapsed:6.1f}s]   repair failed for step "
                          f"{payload['id']}: {payload['reason'][:70]}")

                elif kind == "step.completed":
                    icon = "✓" if payload["ok"] else "✗"
                    detail = payload["summary"] or payload.get("error", "")
                    print(f"[{elapsed:6.1f}s]   {icon} step {payload['id']} "
                          f"({payload['duration_ms']}ms) {detail}")

                elif kind == "artifact.created":
                    print(f"[{elapsed:6.1f}s] 📄 ARTIFACT {payload['kind']}: "
                          f"{payload['relative_path']}")

                elif kind == "run.completed":
                    res = payload["residency"]
                    print("─" * 78)
                    print(f"[{elapsed:6.1f}s] COMPLETED  {payload['steps']} steps · "
                          f"{payload['tokens']} tokens · {payload['elapsed_s']}s")
                    print(f"           budget {res['used_mb']}/{res['budget_mb']} MB · "
                          f"resident: {', '.join(res['resident']) or 'none'}")
                    for artifact in payload["artifacts"]:
                        print(f"           artifact: {artifact['relative_path']}")
                    return 0

                elif kind in {"run.failed", "run.cancelled"}:
                    print("─" * 78)
                    print(f"[{elapsed:6.1f}s] \033[31m{kind.upper()}\033[0m "
                          f"{payload.get('error', '')}")
                    return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
