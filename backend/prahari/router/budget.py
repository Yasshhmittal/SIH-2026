"""Residency manager — the hot-swap controller.

Ollama's own eviction is LRU and not budget-aware, so PRAHARI drives residency
explicitly. That is what makes swap behaviour deterministic, measurable, and
identical between the CPU dev box and the target GPU server: both plan against
a *declared* budget.

Models with `device: cpu` (embeddings) are deliberately off-budget — they are
pinned outside the accelerator so they never trigger a swap.

Everything here is serialised by a single lock. Two steps loading different
models concurrently on a 6 GB budget is exactly the thrash we are preventing.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from ..config import Profile
from ..llm.ollama import OllamaClient
from .registry import ModelSpec, Registry


@dataclass
class SwapEvent:
    """One residency change. Rendered in the UI swap log."""

    loaded: str
    evicted: list[str] = field(default_factory=list)
    load_s: float = 0.0
    was_resident: bool = False
    reason: str = ""
    at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "loaded": self.loaded,
            "evicted": self.evicted,
            "load_s": round(self.load_s, 2),
            "was_resident": self.was_resident,
            "reason": self.reason,
            "at": self.at,
        }


class ResidencyManager:
    def __init__(
        self,
        client: OllamaClient,
        registry: Registry,
        profile: Profile,
    ) -> None:
        self._client = client
        self._registry = registry
        self._profile = profile
        self._lock = threading.RLock()
        self._resident: dict[str, float] = {}      # model_id -> last used (monotonic)
        self._swaps: list[SwapEvent] = []

    # -- state -------------------------------------------------------------

    @property
    def resident(self) -> set[str]:
        with self._lock:
            return set(self._resident)

    def _on_budget(self, spec: ModelSpec) -> bool:
        """CPU-pinned models do not consume the accelerator budget."""
        return spec.device != "cpu"

    def used_mb(self) -> int:
        with self._lock:
            total = 0
            for model_id in self._resident:
                spec = self._registry.get(model_id)
                if spec and self._on_budget(spec):
                    total += spec.mem_mb
            return total

    def state(self) -> dict[str, Any]:
        """Feeds the Models panel: gauge, what's loaded, recent swaps."""
        with self._lock:
            used = self.used_mb()
            return {
                "profile": self._profile.name,
                "label": self._profile.label,
                "accelerator": self._profile.accelerator,
                "budget_mb": self._profile.budget_mb,
                "used_mb": used,
                "free_mb": max(self._profile.budget_mb - used, 0),
                "resident": sorted(self._resident),
                "max_concurrent": self._profile.max_concurrent_models,
                "recent_swaps": [s.to_dict() for s in self._swaps[-12:]],
            }

    def swap_log(self) -> list[dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._swaps]

    # -- residency control -------------------------------------------------

    def sync_from_ollama(self) -> None:
        """Reconcile with reality. Ollama may have evicted behind our back."""
        try:
            live = {m.get("name", "") for m in self._client.loaded_models()}
        except Exception:
            return
        normalised = {n[: -len(":latest")] if n.endswith(":latest") else n for n in live}
        with self._lock:
            for model_id in list(self._resident):
                if model_id not in normalised and model_id not in live:
                    del self._resident[model_id]

    def _victims_for(self, spec: ModelSpec) -> list[str]:
        """Least-recently-used models to evict so `spec` fits the budget."""
        if not self._on_budget(spec):
            return []

        budget = self._profile.budget_mb
        max_models = self._profile.max_concurrent_models

        on_budget = [
            (mid, ts) for mid, ts in self._resident.items()
            if (s := self._registry.get(mid)) and self._on_budget(s)
        ]
        victims: list[str] = []
        used = self.used_mb()

        # Evict LRU first until both the byte budget and the slot count fit.
        for model_id, _ in sorted(on_budget, key=lambda kv: kv[1]):
            fits_bytes = used + spec.mem_mb <= budget
            fits_slots = len(on_budget) - len(victims) + 1 <= max_models
            if fits_bytes and fits_slots:
                break
            victims.append(model_id)
            victim_spec = self._registry.get(model_id)
            if victim_spec:
                used -= victim_spec.mem_mb

        return victims

    def acquire(self, model_id: str, reason: str = "") -> SwapEvent:
        """Make `model_id` resident, evicting whatever must go. Blocking.

        Returns the SwapEvent — including a real measured load time, which is
        the number shown on the timeline.
        """
        spec = self._registry.get(model_id)
        if spec is None:
            raise ValueError(f"model not in registry: {model_id}")

        with self._lock:
            if model_id in self._resident:
                self._resident[model_id] = time.monotonic()
                event = SwapEvent(
                    loaded=model_id, was_resident=True, load_s=0.0,
                    reason=reason or "already resident",
                )
                self._swaps.append(event)
                return event

            victims = self._victims_for(spec)
            for victim in victims:
                self._client.unload(victim)
                self._resident.pop(victim, None)

            load_s = self._client.ensure_loaded(model_id)
            self._resident[model_id] = time.monotonic()

            event = SwapEvent(
                loaded=model_id,
                evicted=victims,
                load_s=load_s,
                was_resident=False,
                reason=reason or "required by step",
            )
            self._swaps.append(event)
            return event

    def prefetch(self, model_id: str, reason: str = "plan lookahead") -> None:
        """Start loading a model we know a later step needs.

        Plan-aware prefetch: because the whole DAG is known up front, a model
        can be loaded during a CPU-bound step (OCR, retrieval, rendering) so
        the swap is already paid for by the time that step arrives. Best-effort
        and non-blocking — failure here must never fail a run.
        """
        if not self._profile.prefetch:
            return
        with self._lock:
            if model_id in self._resident:
                return
            spec = self._registry.get(model_id)
            if spec is None or not spec.available:
                return
            # Only prefetch when it costs no eviction; evicting a model the
            # current step may still need would be worse than the swap.
            if self._victims_for(spec):
                return

        def _load() -> None:
            try:
                self.acquire(model_id, reason=reason)
            except Exception:
                pass

        threading.Thread(target=_load, daemon=True).start()

    def release_all(self) -> None:
        """Evict everything on-budget. Used at shutdown and between demos."""
        with self._lock:
            for model_id in list(self._resident):
                spec = self._registry.get(model_id)
                if spec and self._on_budget(spec):
                    self._client.unload(model_id)
                    del self._resident[model_id]
