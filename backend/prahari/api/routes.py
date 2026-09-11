"""HTTP API. Everything binds to loopback; there is no outbound client here."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from ..agent.loop import get_runner
from ..config import get_settings
from ..events import bus
from ..llm.ollama import get_client
from ..router.registry import get_registry
from ..router.scorer import RoutingRequest, score_models
from ..tools import registry as tools

router = APIRouter(prefix="/api")


# ----------------------------------------------------------------- health ---

@router.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    client = get_client()
    reg = get_registry()

    ollama_up = client.health()
    available = [m.id for m in reg.models.values() if m.available]
    missing = [m.id for m in reg.models.values() if not m.available and not m.optional]

    return {
        "status": "ok" if ollama_up and not missing else "degraded",
        "profile": {
            "name": settings.profile.name,
            "label": settings.profile.label,
            "accelerator": settings.profile.accelerator,
            "budget_mb": settings.profile.budget_mb,
        },
        "ollama": {"reachable": ollama_up, "host": "127.0.0.1:11434"},
        "models": {"available": available, "missing_required": missing},
        "tools": tools.names(),
        "registry_errors": reg.load_errors,
    }


# ----------------------------------------------------------------- models ---

@router.get("/models")
def list_models() -> dict[str, Any]:
    reg = get_registry()
    runner = get_runner()
    runner.residency.sync_from_ollama()

    return {
        "models": [
            {
                "id": m.id,
                "roles": sorted(m.roles),
                "modalities": sorted(m.modalities),
                "mem_mb": m.mem_mb,
                "ctx": m.ctx,
                "quality": m.quality,
                "speed_tps": m.speed_tps,
                "resident_pinned": m.resident,
                "device": m.device,
                "available": m.available,
                "optional": m.optional,
                "notes": m.notes,
            }
            for m in sorted(reg.models.values(), key=lambda s: s.id)
        ],
        "residency": runner.residency.state(),
        "errors": reg.load_errors,
    }


@router.post("/models/reload")
def reload_models() -> dict[str, Any]:
    """Re-read models.yaml and re-check what is pulled.

    This is the "add a model without redesigning the system" demo: append an
    entry, pull it, call this, and it appears in the router table.
    """
    reg = get_runner().refresh_registry()
    return {
        "reloaded": True,
        "count": len(reg.models),
        "available": [m.id for m in reg.models.values() if m.available],
        "errors": reg.load_errors,
    }


class RoutePreview(BaseModel):
    role: str = Field(description="reason | plan | code | vision | embed | ...")
    modalities: list[str] = Field(default_factory=lambda: ["text"])
    est_prompt_tokens: int = 2000
    est_output_tokens: int = 512
    quality_critical: bool = False


@router.post("/route/preview")
def route_preview(body: RoutePreview) -> dict[str, Any]:
    """Score a hypothetical step without running anything.

    Lets the router be demonstrated on its own, and lets a judge poke at it.
    """
    runner = get_runner()
    runner.residency.sync_from_ollama()
    decision = score_models(
        get_registry(),
        RoutingRequest(
            role=body.role,
            modalities=frozenset(body.modalities),
            est_prompt_tokens=body.est_prompt_tokens,
            est_output_tokens=body.est_output_tokens,
            quality_critical=body.quality_critical,
        ),
        get_settings().profile,
        runner.residency.resident,
    )
    return decision.to_dict()


# ------------------------------------------------------------------- runs ---

class StartRun(BaseModel):
    prompt: str
    org_id: str = "mrpl"


@router.post("/runs")
def start_run(body: StartRun) -> dict[str, str]:
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is empty")
    run_id = get_runner().start(body.prompt.strip(), org_id=body.org_id)
    return {"run_id": run_id}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    state = get_runner().get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="unknown run")
    return {
        "run_id": state.run_id,
        "org_id": state.org_id,
        "prompt": state.prompt,
        "task": state.task.model_dump(mode="json") if state.task else None,
        "plan": state.plan.model_dump(mode="json") if state.plan else None,
        "observations": state.observations,
        "artifacts": state.artifacts,
        "elapsed_s": round(state.elapsed, 1),
        "tokens": state.tokens,
    }


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, bool]:
    return {"cancelled": get_runner().cancel(run_id)}


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str) -> EventSourceResponse:
    """SSE stream of the agent timeline. Replays history, then follows live."""

    async def generator():
        async for event in bus.subscribe(run_id):
            yield {"event": event.type, "id": str(event.seq),
                   "data": json.dumps(event.to_dict())}

    return EventSourceResponse(generator())


# ------------------------------------------------------------------ tools ---

@router.get("/tools")
def list_tools() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": spec.name,
                "description": spec.description,
                "capabilities": sorted(spec.capabilities),
                "args_schema": spec.args_schema,
                "returns": spec.returns,
            }
            for spec in sorted(tools.all(), key=lambda s: s.name)
        ],
        "note": (
            "Deny-by-default. There is deliberately no network tool and no "
            "shell tool in this registry."
        ),
    }
