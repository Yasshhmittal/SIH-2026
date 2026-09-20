"""The agent control loop.

    RECEIVE → CLASSIFY → PLAN → [SELECT → EXECUTE → OBSERVE → CRITIC]* → DELIVER

Two properties matter more than anything else here:

1. **Code owns the control flow.** The model classifies, plans, and judges —
   but the loop, the budgets, and the tool dispatch are ordinary Python. A 1.5B
   model cannot wander off, because there is nowhere to wander to.

2. **Every LLM call is schema-constrained.** `schema_of(Plan)` is handed to
   Ollama as a decoding constraint, so a malformed plan is not caught and
   retried — it is unrepresentable.

Model selection happens per *step*, not per run, which is why a single task can
visibly move between a vision model, a text model, and a coder.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import ORGS_DIR, Settings, get_settings
from ..events import bus
from ..llm.ollama import OllamaClient, get_client
from ..router.budget import ResidencyManager
from ..router.registry import Registry, get_registry
from ..router.scorer import RoutingRequest, score_models
from ..tools import DEFAULT_GRANTS, ToolContext, registry as tools
from .extract import extract_values
from .hints import detect_signals, reconcile
from .recipes import build_plan, select_recipe
from .schemas import Plan, PlanStep, TaskSpec, schema_of

# Which model role each tool needs, if any. Tools absent from this map are
# pure compute and cost no model time at all — which is what makes plan-aware
# prefetch worthwhile: the loop knows in advance where the CPU-only gaps are.
TOOL_ROLE: dict[str, str] = {
    "vision.ask": "vision",
    "ocr.page": "vision",
    "code.run": "code",
    "llm.write": "write",
}

# Realistic (prompt, output) token estimates per role. These drive the router's
# context gate, so they must reflect what a step actually sends — a vision
# question is a short string plus an image, not a 2000-token document, and
# guessing high here silently disqualifies small-context vision models.
ROLE_ESTIMATES: dict[str, tuple[int, int]] = {
    "classify": (400, 160),
    "plan": (1200, 700),
    "vision": (300, 400),
    "ocr_assist": (300, 700),
    "code": (1500, 900),
    "extract": (2500, 800),
    "write": (3000, 1200),
    "summarize": (3000, 600),
    "reason": (2000, 800),
}

VISION_ROLES = {"vision", "ocr_assist", "diagram"}

# Observation summaries that justify a repair attempt. Argument problems are
# worth retrying; a genuine failure inside the tool is not.
_REPAIRABLE = {
    "unknown formula",
    "invalid arguments",
    "missing inputs",
    "parse error",
    "non-numeric input",
}


def routing_request_for(role: str, *, quality_critical: bool = False) -> RoutingRequest:
    prompt_tokens, output_tokens = ROLE_ESTIMATES.get(role, (2000, 512))
    modalities = frozenset({"text", "image"}) if role in VISION_ROLES else frozenset({"text"})
    return RoutingRequest(
        role=role,
        modalities=modalities,
        est_prompt_tokens=prompt_tokens,
        est_output_tokens=output_tokens,
        quality_critical=quality_critical,
    )

CLASSIFY_SYSTEM = """You classify industrial knowledge-work requests for an
air-gapped refinery assistant. Reply only with the required JSON object.

Choosing `deliverable`:
  docx   — an approval note, noting sheet, memo, letter or written report
  xlsx   — a spreadsheet or workbook
  pptx   — a presentation or slide deck
  code   — a script, program or function the user will run
  answer — a question to answer in prose, with no file
  none   — nothing to produce

Setting capability flags — set true when the request needs it, even implicitly:
  needs_calculation — any arithmetic, rate, remaining life, or "show the steps"
  needs_vision      — a scan, drawing, P&ID, photograph or handwriting
  needs_code        — code must be written or executed
  needs_retrieval   — an SOP, manual, standard or past document must be consulted

"Draft an approval note ... show the corrosion rate calculation" is
deliverable=docx with needs_calculation=true. It is NOT deliverable=code."""

PLAN_SYSTEM = """You plan multi-step work for an air-gapped industrial assistant.

Rules:
- Use ONLY tools from the provided list. Never invent a tool name.
- Keep the plan minimal: the fewest steps that actually finish the job.
- The final step must produce the deliverable the user asked for.
- Reference earlier steps through depends_on, not by copying their output.
- Arguments must be concrete values taken from the request, not descriptions
  of values. If the request states a number, put that number in the args.
- Follow the tool's stated argument names exactly.
- CRITICAL: If the task needs information from documents, kb.search MUST be
  the FIRST step. Never call docx.render without calling kb.search first."""


def _dig(payload: Any, path: str) -> Any:
    """Walk a dotted path into an observation record, or None."""
    current = payload
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current.get(segment)
        else:
            return None
    return current


def resolve_refs(value: Any, observations: dict[int, dict[str, Any]]) -> Any:
    """Substitute {"$from_step": n, "path": ...} with real observed values.

    Recipes are written before any step has run, so they reference results
    positionally. Resolution happens immediately before invocation, which means
    a step always receives concrete data — never a placeholder that some tool
    then has to interpret.
    """
    if isinstance(value, dict):
        if "$from_step" in value:
            record = observations.get(int(value["$from_step"]))
            if record is None or not record.get("ok"):
                return None
            return _dig(record, value.get("path", "data"))

        if "$from_steps" in value:
            collected = []
            for step_id in value["$from_steps"]:
                record = observations.get(int(step_id))
                if record is None or not record.get("ok"):
                    continue
                found = _dig(record, value.get("path", "data"))
                if found is None:
                    continue
                if isinstance(found, list):
                    collected.extend(found)
                else:
                    collected.append(found)
            return collected

        return {k: resolve_refs(v, observations) for k, v in value.items()}

    if isinstance(value, list):
        return [resolve_refs(item, observations) for item in value]

    return value


@dataclass
class RunState:
    run_id: str
    org_id: str
    prompt: str
    workspace: Path
    started_at: float = field(default_factory=time.time)
    task: TaskSpec | None = None
    plan: Plan | None = None
    values: Any = None
    observations: dict[int, dict[str, Any]] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    replans: int = 0
    tokens: int = 0
    cancelled: bool = False
    history: list[dict[str, str]] = field(default_factory=list)

    @property
    def elapsed(self) -> float:
        return time.time() - self.started_at


class AgentRunner:
    def __init__(
        self,
        client: OllamaClient | None = None,
        model_registry: Registry | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or get_client()
        self._registry = model_registry or get_registry()
        self._residency = ResidencyManager(
            self._client, self._registry, self._settings.profile
        )
        self._runs: dict[str, RunState] = {}

    # -- public API --------------------------------------------------------

    @property
    def residency(self) -> ResidencyManager:
        return self._residency

    def refresh_registry(self) -> Registry:
        """Hot-reload models.yaml. Backs the live 'add a model' demo."""
        self._registry = get_registry(refresh=True)
        self._residency._registry = self._registry  # keep the manager in sync
        return self._registry

    def start(self, prompt: str, org_id: str = "mrpl",
              history: list[dict[str, str]] | None = None) -> str:
        run_id = uuid.uuid4().hex[:12]
        workspace = ORGS_DIR / org_id / "workspace" / run_id
        workspace.mkdir(parents=True, exist_ok=True)

        state = RunState(run_id=run_id, org_id=org_id, prompt=prompt,
                         workspace=workspace, history=history or [])
        self._runs[run_id] = state

        threading.Thread(target=self._execute, args=(state,), daemon=True).start()
        return run_id

    @staticmethod
    def _history_messages(history: list[dict[str, str]],
                          max_turns: int = 6) -> list[dict[str, str]]:
        """Convert the conversation history into chat messages for the LLM.

        Keeps only the last `max_turns` exchanges to stay within context
        budgets. Each entry in `history` has {role, content}.
        """
        # Take only the most recent turns
        recent = history[-(max_turns * 2):] if history else []
        return [{"role": h["role"], "content": h["content"]} for h in recent]

    def cancel(self, run_id: str) -> bool:
        state = self._runs.get(run_id)
        if state is None:
            return False
        state.cancelled = True
        return True

    def get(self, run_id: str) -> RunState | None:
        return self._runs.get(run_id)

    # -- routing -----------------------------------------------------------

    def _route(self, run_id: str, req: RoutingRequest, label: str) -> str | None:
        """Score, publish the decision table, then make the winner resident."""
        self._residency.sync_from_ollama()
        decision = score_models(
            self._registry, req, self._settings.profile, self._residency.resident
        )
        bus.publish(run_id, "router.decision",
                    {"label": label, **decision.to_dict()})

        if decision.chosen is None:
            return None

        swap = self._residency.acquire(decision.chosen, reason=label)
        if not swap.was_resident:
            bus.publish(run_id, "router.swap", swap.to_dict())
        return decision.chosen

    def _prefetch_next_model(self, state: RunState, from_index: int) -> None:
        """Look ahead in the plan and warm the next model during CPU work."""
        if state.plan is None:
            return
        for step in state.plan.steps[from_index:]:
            role = TOOL_ROLE.get(step.tool)
            if role is None:
                continue
            decision = score_models(
                self._registry,
                routing_request_for(role),
                self._settings.profile,
                self._residency.resident,
            )
            if decision.chosen:
                self._residency.prefetch(decision.chosen)
            return

    # -- LLM stages --------------------------------------------------------

    def _classify(self, state: RunState) -> TaskSpec:
        bus.publish(state.run_id, "stage.started", {"stage": "classify"})

        model = self._route(
            state.run_id,
            routing_request_for("classify"),
            label="classify intent",
        )
        if model is None:
            raise RuntimeError("no model available for classification")

        signals = detect_signals(state.prompt)
        evidence = signals.as_prompt_evidence()
        user = state.prompt if not evidence else f"{state.prompt}\n\n[{evidence}]"

        messages = [{"role": "system", "content": CLASSIFY_SYSTEM}]
        messages.extend(self._history_messages(state.history, max_turns=3))
        messages.append({"role": "user", "content": user})

        gen = self._client.chat(
            model,
            messages,
            schema=schema_of(TaskSpec),
            temperature=0.0,
            num_predict=320,
        )
        state.tokens += gen.prompt_tokens + gen.output_tokens
        task = TaskSpec.model_validate_json(gen.text)

        # Code corrects the classifier where an explicit phrase contradicts it,
        # and publishes the correction so it is never a silent override.
        task, corrections = reconcile(task, signals)
        if corrections:
            bus.publish(state.run_id, "classify.reconciled", {
                "corrections": corrections,
                "signals": signals.to_dict(),
            })

        bus.publish(state.run_id, "stage.completed", {
            "stage": "classify",
            "model": model,
            "task": task.model_dump(mode="json"),
            "signals": signals.to_dict(),
            "duration_s": round(gen.total_s, 2),
            "tokens_per_second": round(gen.tokens_per_second, 1),
        })
        return task

    def _plan(self, state: RunState, task: TaskSpec) -> Plan:
        bus.publish(state.run_id, "stage.started", {"stage": "plan"})

        # A recipe wins whenever one matches: control flow becomes code, and
        # the ~55s freehand planning call is skipped entirely. Measured on this
        # box, the flagship task went from 60s to 12s this way.
        values = extract_values(state.prompt)
        state.values = values

        if values.warnings:
            # An implausible parse means the extracted numbers cannot be
            # trusted as recipe arguments. Fall back to freehand planning
            # rather than compute confidently from a misread.
            bus.publish(state.run_id, "extract.warning", {
                "warnings": values.warnings,
                "extracted": values.as_dict(),
                "action": "recipe declined, falling back to freehand planning",
            })
            recipe = None
        else:
            recipe = select_recipe(task, values)

        if recipe is not None:
            plan = build_plan(recipe, state.prompt, task, values)
            plan = self._sanitise_plan(state, plan)
            bus.publish(state.run_id, "plan.created", {
                "source": "recipe",
                "recipe": recipe.name,
                "goal": plan.goal,
                "steps": [s.model_dump(mode="json") for s in plan.steps],
                "extracted": values.as_dict(),
                "duration_s": 0.0,
            })
            return plan

        return self._plan_freehand(state, task, values)

    def _plan_freehand(self, state: RunState, task: TaskSpec, values: Any) -> Plan:
        model = self._route(
            state.run_id,
            routing_request_for("plan"),
            label="build plan",
        )
        if model is None:
            raise RuntimeError("no model available for planning")

        required: list[str] = []
        if task.needs_retrieval:
            required.append("consult org documents (use kb.search)")
        if task.needs_vision:
            required.append("look at a scan or drawing (use ocr.page or vision.ask)")
        if task.needs_calculation:
            required.append("compute numbers with steps shown (use calc.evaluate)")
        if task.needs_code:
            required.append("write and verify code (use code.run)")

        evidence = values.as_prompt_evidence() if values else ""

        user = (
            f"Request: {state.prompt}\n\n"
            f"Classified as: {task.kind.value}\n"
            f"Expected deliverable: {task.deliverable}\n"
            + (f"This task must: {'; '.join(required)}.\n" if required else "")
            + (f"{evidence}\n" if evidence else "")
            + f"\nAvailable tools:\n{tools.describe_for_planner()}\n\n"
            "Produce the plan."
        )

        history_msgs = self._history_messages(state.history, max_turns=4)

        for attempt in range(3):
            plan_messages = [{"role": "system", "content": PLAN_SYSTEM}]
            plan_messages.extend(history_msgs)
            plan_messages.append({"role": "user", "content": user})

            gen = self._client.chat(
                model,
                plan_messages,
                schema=schema_of(Plan),
                temperature=0.4,
                num_predict=1400,
            )
            state.tokens += gen.prompt_tokens + gen.output_tokens
            
            try:
                plan = Plan.model_validate_json(gen.text)
                plan = self._sanitise_plan(state, plan)
                break
            except Exception as e:
                if attempt == 2:
                    raise RuntimeError(f"Planner failed to generate a valid plan: {e}")
                continue

        bus.publish(state.run_id, "plan.created", {
            "source": "freehand",
            "recipe": None,
            "model": model,
            "goal": plan.goal,
            "steps": [s.model_dump(mode="json") for s in plan.steps],
            "duration_s": round(gen.total_s, 2),
            "tokens_per_second": round(gen.tokens_per_second, 1),
        })
        return plan

    def _sanitise_plan(self, state: RunState, plan: Plan) -> Plan:
        """Drop steps naming tools that do not exist, and renumber.

        Constrained decoding guarantees the plan *parses*; it cannot guarantee
        the tool names are real. This is the second gate, and it runs before
        anything executes.
        """
        kept: list[PlanStep] = []
        dropped: list[dict[str, str]] = []

        for step in plan.steps:
            ok, reason = tools.validate_call(step.tool, step.args)
            if ok:
                kept.append(step)
            else:
                dropped.append({"tool": step.tool, "reason": reason})

        if dropped:
            bus.publish(state.run_id, "plan.repaired", {"dropped": dropped})

        for index, step in enumerate(kept, start=1):
            step.id = index

        budget = self._settings.agent.max_steps
        if len(kept) > budget:
            kept = kept[:budget]
            bus.publish(state.run_id, "plan.truncated", {"max_steps": budget})

        return Plan(goal=plan.goal, steps=kept)

    # -- execution ---------------------------------------------------------

    REPAIR_SYSTEM = """A planned tool call failed validation. Fix it.

Return a single corrected tool call. Use the tool's argument names exactly.
If the tool lists allowed values, pick one from that list. If arguments are
missing, supply them from the original request. Do not change the tool."""

    def _repair_step(
        self, state: RunState, step: PlanStep, error: str
    ) -> PlanStep | None:
        """Ask the model to fix one failed tool call, once.

        This is the inner repair loop: the outer loop replans a *sequence*,
        this fixes a single call. Bounded to one attempt per step and counted
        against the replan budget, so a stubborn failure cannot spin.
        """
        if state.replans >= self._settings.agent.max_replans:
            return None

        spec = tools.get(step.tool)
        if spec is None:
            return None

        model = self._route(
            state.run_id,
            routing_request_for("plan"),
            label=f"repair step {step.id}",
        )
        if model is None:
            return None

        user = (
            f"Original request: {state.prompt}\n\n"
            f"Tool: {spec.name}\n"
            f"Description: {spec.description}\n"
            f"Argument schema:\n{json.dumps(spec.args_schema, indent=2)}\n\n"
            f"Attempted args:\n{json.dumps(step.args, indent=2)}\n\n"
            f"Validation error: {error}\n\n"
            "Return the corrected arguments."
        )

        try:
            gen = self._client.chat(
                model,
                [{"role": "system", "content": self.REPAIR_SYSTEM},
                 {"role": "user", "content": user}],
                schema=spec.args_schema,
                temperature=0.0,
                num_predict=500,
            )
        except Exception:
            return None

        state.tokens += gen.prompt_tokens + gen.output_tokens
        state.replans += 1

        try:
            new_args = json.loads(gen.text)
        except json.JSONDecodeError:
            return None

        repaired = step.model_copy(update={"args": new_args})
        ok, reason = tools.validate_call(repaired.tool, repaired.args)
        if not ok:
            bus.publish(state.run_id, "step.repair_failed",
                        {"id": step.id, "tool": step.tool, "reason": reason})
            return None

        bus.publish(state.run_id, "step.repaired", {
            "id": step.id,
            "tool": step.tool,
            "before": step.args,
            "after": new_args,
            "fixed": error,
            "replans_used": state.replans,
        })
        return repaired

    def _execute_step(self, state: RunState, step: PlanStep, index: int) -> dict[str, Any]:
        # Recipe steps reference earlier results positionally; resolve them to
        # concrete values now, before anything is invoked or validated.
        resolved_args = resolve_refs(step.args, state.observations)

        bus.publish(state.run_id, "step.started", {
            "id": step.id, "tool": step.tool, "why": step.why,
            "args": resolved_args,
        })

        model_used: str | None = None
        role = TOOL_ROLE.get(step.tool)
        if role:
            model_used = self._route(
                state.run_id,
                routing_request_for(role),
                label=f"step {step.id}: {step.tool}",
            )

        # Warm the next model-bearing step while this one runs on CPU.
        self._prefetch_next_model(state, index + 1)

        ctx = ToolContext(
            run_id=state.run_id,
            org_id=state.org_id,
            workspace=state.workspace,
            emit=lambda t, p: bus.publish(state.run_id, t, p),
        )
        observation = tools.invoke(step.tool, ctx, resolved_args, DEFAULT_GRANTS)

        # A rejected call is usually a malformed argument, not a bad idea.
        # One bounded repair attempt before the step is written off.
        if not observation.ok and observation.summary in _REPAIRABLE:
            repaired = self._repair_step(
                state, step, observation.error or observation.summary
            )
            if repaired is not None:
                resolved_args = resolve_refs(repaired.args, state.observations)
                step.args = repaired.args
                observation = tools.invoke(
                    step.tool, ctx, resolved_args, DEFAULT_GRANTS
                )

        record = {
            "id": step.id,
            "tool": step.tool,
            "ok": observation.ok,
            "summary": observation.summary,
            "data": observation.data,
            "error": observation.error,
            "duration_ms": observation.duration_ms,
            "model": model_used,
        }
        state.observations[step.id] = record

        if observation.ok and observation.data.get("artifact_kind"):
            artifact = {
                "kind": observation.data["artifact_kind"],
                "filename": observation.data.get("filename"),
                "relative_path": observation.data.get("relative_path"),
                "step_id": step.id,
            }
            state.artifacts.append(artifact)
            bus.publish(state.run_id, "artifact.created", artifact)

        bus.publish(state.run_id, "step.completed", record)
        return record

    def _synthesize(self, state: RunState) -> str | None:
        bus.publish(state.run_id, "stage.started", {"stage": "synthesize"})
        model = self._route(
            state.run_id,
            routing_request_for("write"),
            label="synthesize answer",
        )
        if model is None:
            return None

        context_lines = []
        for obs in state.observations.values():
            if obs.get("ok") and isinstance(obs.get("data"), dict):
                chunks = obs["data"].get("chunks", []) + obs["data"].get("citations", [])
                for chunk in chunks:
                    context_lines.append(f"[{chunk.get('document', 'unknown')}] {chunk.get('text', '')}")

        context_text = "\n\n".join(context_lines)
        system = (
            "You are a helpful industrial assistant. Answer the user's question using only "
            "the provided context. If the context does not contain the answer, say so."
        )
        user_prompt = f"Context:\n{context_text}\n\nQuestion: {state.prompt}"

        messages = [{"role": "system", "content": system}]
        messages.extend(self._history_messages(state.history, max_turns=6))
        messages.append({"role": "user", "content": user_prompt})

        gen = self._client.chat(
            model,
            messages,
        )
        state.tokens += gen.prompt_tokens + gen.output_tokens
        return gen.text

    # -- the loop ----------------------------------------------------------

    def _execute(self, state: RunState) -> None:
        budget = self._settings.agent
        bus.publish(state.run_id, "run.started", {
            "run_id": state.run_id,
            "org_id": state.org_id,
            "prompt": state.prompt,
            "profile": self._settings.profile.name,
            "budget": {
                "max_steps": budget.max_steps,
                "max_replans": budget.max_replans,
                "wall_clock_s": budget.wall_clock_s,
            },
        })

        try:
            state.task = self._classify(state)
            state.plan = self._plan(state, state.task)

            if not state.plan.steps:
                bus.publish(state.run_id, "run.failed",
                            {"error": "planner produced no executable steps"})
                return

            for index, step in enumerate(state.plan.steps):
                if state.cancelled:
                    bus.publish(state.run_id, "run.cancelled", {"at_step": step.id})
                    return
                if state.elapsed > budget.wall_clock_s:
                    bus.publish(state.run_id, "run.failed", {
                        "error": f"wall-clock budget of {budget.wall_clock_s}s exhausted",
                        "completed_steps": index,
                    })
                    return
                if state.tokens > budget.max_tokens_per_run:
                    bus.publish(state.run_id, "run.failed", {
                        "error": "token budget exhausted",
                        "completed_steps": index,
                    })
                    return

                self._execute_step(state, step, index)

            answer = None
            if state.task and state.task.deliverable in {"answer", "none"}:
                answer = self._synthesize(state)

            bus.publish(state.run_id, "run.completed", {
                "steps": len(state.plan.steps),
                "artifacts": state.artifacts,
                "answer": answer,
                "elapsed_s": round(state.elapsed, 1),
                "tokens": state.tokens,
                "residency": self._residency.state(),
            })

        except Exception as exc:
            bus.publish(state.run_id, "run.failed", {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_s": round(state.elapsed, 1),
            })


_runner: AgentRunner | None = None


def get_runner() -> AgentRunner:
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner
