"""Local Ollama client.

The only component in PRAHARI that speaks HTTP, and it speaks it exclusively to
127.0.0.1. Two things here matter beyond plumbing:

1. `chat_structured` uses Ollama's JSON-Schema constrained decoding. A 3B model
   asked to free-form a plan will emit broken JSON; constrained, it *cannot*.
   This is what makes small-model agency reliable.

2. `unload` / `ensure_loaded` give the router explicit control over what sits in
   memory. Ollama's own eviction is not budget-aware, so we drive it ourselves.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable

import httpx

from ..config import OLLAMA_HOST


class OllamaError(RuntimeError):
    pass


@dataclass
class Generation:
    """One completion, with the measurements the router feeds on."""

    text: str
    model: str
    prompt_tokens: int
    output_tokens: int
    total_s: float
    load_s: float

    @property
    def tokens_per_second(self) -> float:
        gen_s = max(self.total_s - self.load_s, 1e-6)
        return self.output_tokens / gen_s


class OllamaClient:
    def __init__(self, host: str = OLLAMA_HOST, timeout: float = 600.0) -> None:
        self._host = host.rstrip("/")
        # Long timeout: 7B generation on CPU is genuinely slow, and a premature
        # client timeout looks exactly like a hang.
        self._client = httpx.Client(base_url=self._host, timeout=timeout)

    # -- introspection -----------------------------------------------------

    def list_models(self) -> list[str]:
        r = self._client.get("/api/tags")
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

    def loaded_models(self) -> list[dict[str, Any]]:
        """What is resident right now — the ground truth behind the VRAM gauge."""
        r = self._client.get("/api/ps")
        r.raise_for_status()
        return r.json().get("models", [])

    def health(self) -> bool:
        try:
            self._client.get("/api/tags", timeout=3.0).raise_for_status()
            return True
        except Exception:
            return False

    # -- residency control -------------------------------------------------

    def unload(self, model: str) -> None:
        """Evict a model immediately (keep_alive=0).

        The router calls this before loading a model that would breach the
        declared budget. This is what makes hot-swap deterministic instead of
        leaving it to Ollama's own LRU.
        """
        try:
            self._client.post(
                "/api/generate",
                json={"model": model, "prompt": "", "keep_alive": 0},
            )
        except Exception:
            # Unload is best-effort: a model that is already gone is a success.
            pass

    def ensure_loaded(self, model: str, keep_alive: str = "30m") -> float:
        """Load a model and return how long it took, in seconds.

        Issues an empty generation, which forces the load without producing
        tokens. The returned duration is the number shown in the swap log.
        """
        started = time.perf_counter()
        r = self._client.post(
            "/api/generate",
            json={"model": model, "prompt": "", "keep_alive": keep_alive},
        )
        if r.status_code != 200:
            raise OllamaError(f"failed to load {model}: {r.text[:200]}")
        return time.perf_counter() - started

    # -- generation --------------------------------------------------------

    def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
        num_predict: int = 1024,
        images: Iterable[str] | None = None,
        keep_alive: str = "30m",
    ) -> Generation:
        """One chat turn.

        `schema` enables constrained decoding — pass a JSON Schema and the
        output is guaranteed to parse and conform.
        `images` are base64 strings, attached to the final user message.
        """
        msgs = [dict(m) for m in messages]
        if images:
            img_list = list(images)
            if img_list:
                msgs[-1]["images"] = img_list

        payload: dict[str, Any] = {
            "model": model,
            "messages": msgs,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        if schema is not None:
            payload["format"] = schema

        started = time.perf_counter()
        r = self._client.post("/api/chat", json=payload)
        total_s = time.perf_counter() - started

        if r.status_code != 200:
            raise OllamaError(f"{model} chat failed [{r.status_code}]: {r.text[:300]}")

        body = r.json()
        return Generation(
            text=body.get("message", {}).get("content", ""),
            model=model,
            prompt_tokens=int(body.get("prompt_eval_count", 0)),
            output_tokens=int(body.get("eval_count", 0)),
            total_s=total_s,
            load_s=float(body.get("load_duration", 0)) / 1e9,
        )

    def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        """Batch-embed. Runs on CPU by design; see models.yaml."""
        r = self._client.post(
            "/api/embed",
            json={"model": model, "input": texts, "keep_alive": "60m"},
        )
        if r.status_code != 200:
            raise OllamaError(f"embed failed [{r.status_code}]: {r.text[:300]}")
        return r.json().get("embeddings", [])

    def close(self) -> None:
        self._client.close()


_client: OllamaClient | None = None


def get_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
