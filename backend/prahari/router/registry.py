"""Model registry: load, validate, and hot-reload config/models.yaml.

Adding a model is one YAML entry plus `ollama pull`. That claim is only true if
nothing else in the codebase hardcodes a model name — so every consumer asks
this registry by *role*, never by id.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..config import MODELS_YAML


@dataclass(frozen=True)
class ModelSpec:
    id: str
    roles: frozenset[str]
    modalities: frozenset[str]
    mem_mb: int
    ctx: int
    quality: float
    speed_tps: float | None = None
    resident: bool = False
    device: str = "auto"
    optional: bool = False
    notes: str = ""

    # Set at load time by checking against `ollama list`.
    available: bool = True

    def supports(self, role: str, modalities: frozenset[str]) -> bool:
        return role in self.roles and modalities <= self.modalities


@dataclass
class Registry:
    models: dict[str, ModelSpec] = field(default_factory=dict)
    source_path: Path = MODELS_YAML
    load_errors: list[str] = field(default_factory=list)

    def by_role(self, role: str) -> list[ModelSpec]:
        return [m for m in self.models.values() if role in m.roles and m.available]

    def get(self, model_id: str) -> ModelSpec | None:
        return self.models.get(model_id)

    @property
    def resident_models(self) -> list[ModelSpec]:
        return [m for m in self.models.values() if m.resident and m.available]


def _normalise(tag: str) -> str:
    """Ollama reports `moondream:latest`; the registry may say `moondream`."""
    return tag[: -len(":latest")] if tag.endswith(":latest") else tag


def _spec_from_dict(raw: dict[str, Any], available_tags: set[str] | None) -> ModelSpec:
    model_id = raw["id"]
    if available_tags is None:
        available = True          # could not query Ollama; assume present
    else:
        available = _normalise(model_id) in available_tags

    return ModelSpec(
        id=model_id,
        roles=frozenset(raw.get("roles", [])),
        modalities=frozenset(raw.get("modalities", ["text"])),
        mem_mb=int(raw["mem_mb"]),
        ctx=int(raw.get("ctx", 8192)),
        quality=float(raw.get("quality", 0.5)),
        speed_tps=raw.get("speed_tps"),
        resident=bool(raw.get("resident", False)),
        device=raw.get("device", "auto"),
        optional=bool(raw.get("optional", False)),
        notes=raw.get("notes", ""),
        available=available,
    )


_lock = threading.Lock()
_registry: Registry | None = None


def load_registry(available_tags: set[str] | None = None) -> Registry:
    """Parse models.yaml and mark which entries are actually pulled.

    `available_tags` comes from `ollama list`. Pass None to skip the check
    (useful in tests). A registry entry that is not pulled stays in the table
    but is hard-gated out of routing, and the UI shows it greyed with a reason.
    """
    with MODELS_YAML.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    reg = Registry()
    for entry in raw.get("models", []):
        try:
            spec = _spec_from_dict(entry, available_tags)
        except (KeyError, ValueError, TypeError) as exc:
            reg.load_errors.append(f"{entry.get('id', '<no id>')}: {exc}")
            continue

        if spec.id in reg.models:
            reg.load_errors.append(f"duplicate model id: {spec.id}")
            continue
        reg.models[spec.id] = spec

    if not reg.models:
        reg.load_errors.append("registry is empty")
    return reg


def get_registry(refresh: bool = False) -> Registry:
    """Process-wide registry. `refresh=True` re-reads YAML and re-checks Ollama.

    The live "add a model in front of the judges" demo is a call to this with
    refresh=True, via POST /api/models/reload.
    """
    global _registry
    with _lock:
        if _registry is None or refresh:
            tags: set[str] | None
            try:
                from ..llm.ollama import get_client

                tags = {_normalise(t) for t in get_client().list_models()}
            except Exception:
                tags = None
            _registry = load_registry(tags)
        return _registry
