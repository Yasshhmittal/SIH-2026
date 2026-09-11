"""Configuration: deployment profile, model registry paths, runtime settings.

Everything tunable lives in config/*.yaml. This module loads it, validates it,
and hands back typed objects. Nothing here reaches the network.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# --- paths ----------------------------------------------------------------
# Resolved relative to the repo root so the app runs from any cwd.
ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
ORGS_DIR = DATA_DIR / "orgs"
RUNTIME_DIR = DATA_DIR / "runtime"

MODELS_YAML = CONFIG_DIR / "models.yaml"
PROFILES_YAML = CONFIG_DIR / "profiles.yaml"

# Ollama is always local. This is not configurable to a remote host by design —
# a remote inference endpoint would break the sovereignty guarantee.
OLLAMA_HOST = "http://127.0.0.1:11434"

QDRANT_PATH = RUNTIME_DIR / "qdrant"        # embedded mode fallback
QDRANT_URL = os.environ.get("PRAHARI_QDRANT_URL", "http://127.0.0.1:6333")
SQLITE_PATH = RUNTIME_DIR / "prahari.db"


@dataclass(frozen=True)
class Weights:
    """Router scoring weights. See router/scorer.py for how they combine."""

    quality: float = 1.0
    context: float = 0.30
    latency: float = 0.25
    swap: float = 0.55
    pressure: float = 0.20


@dataclass(frozen=True)
class Profile:
    """A deployment profile: the resource budget the router plans against.

    The budget is *declared*, not probed. Production wants a hard ceiling
    regardless of what the card reports, and declaring it means the router
    behaves identically on a CPU dev box and the target GPU server.
    """

    name: str
    label: str
    accelerator: str          # cpu | cuda
    budget_mb: int
    max_concurrent_models: int
    weights: Weights
    step_timeout_s: int
    prefetch: bool


@dataclass(frozen=True)
class AgentBudget:
    """Hard stops. The agent returns partial results rather than looping."""

    max_steps: int = 14
    max_replans: int = 2
    max_sandbox_retries: int = 3
    wall_clock_s: int = 900
    max_tokens_per_run: int = 120_000


@dataclass(frozen=True)
class Settings:
    profile: Profile
    agent: AgentBudget
    profiles: dict[str, Profile] = field(default_factory=dict)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing config file: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _profile_from_dict(name: str, raw: dict[str, Any]) -> Profile:
    return Profile(
        name=name,
        label=raw.get("label", name),
        accelerator=raw.get("accelerator", "cpu"),
        budget_mb=int(raw["budget_mb"]),
        max_concurrent_models=int(raw.get("max_concurrent_models", 1)),
        weights=Weights(**(raw.get("weights") or {})),
        step_timeout_s=int(raw.get("step_timeout_s", 120)),
        prefetch=bool(raw.get("prefetch", True)),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    raw = _read_yaml(PROFILES_YAML)
    profiles = {
        name: _profile_from_dict(name, body)
        for name, body in (raw.get("profiles") or {}).items()
    }
    if not profiles:
        raise ValueError("profiles.yaml defines no profiles")

    # PRAHARI_PROFILE wins over the file's `active:` key.
    active = os.environ.get("PRAHARI_PROFILE") or raw.get("active")
    if active not in profiles:
        raise ValueError(
            f"active profile {active!r} not found. available: {sorted(profiles)}"
        )

    return Settings(
        profile=profiles[active],
        agent=AgentBudget(**(raw.get("agent") or {})),
        profiles=profiles,
    )


def ensure_dirs() -> None:
    """Create the runtime directory tree. Safe to call repeatedly."""
    for d in (DATA_DIR, ORGS_DIR, RUNTIME_DIR, QDRANT_PATH):
        d.mkdir(parents=True, exist_ok=True)
