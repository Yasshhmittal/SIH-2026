"""Run event bus.

The agent loop runs in a worker thread (Ollama calls are blocking), while SSE
delivery is async. This bridges the two: `publish` is thread-safe, `subscribe`
is an async iterator.

Every event is also the audit trail's raw material — same payloads, one
hash-chained, one streamed to the browser.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class Event:
    run_id: str
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    seq: int = 0
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "type": self.type,
            "payload": self.payload,
            "seq": self.seq,
            "ts": self.ts,
        }


# Terminal event types — the SSE stream closes after one of these.
TERMINAL = {"run.completed", "run.failed", "run.cancelled"}


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[Event]]] = {}
        self._history: dict[str, list[Event]] = {}
        self._seq: dict[str, int] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = asyncio.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once at startup so worker threads can hand events back."""
        self._loop = loop

    # -- producing ---------------------------------------------------------

    def publish(self, run_id: str, type_: str, payload: dict[str, Any] | None = None) -> Event:
        """Thread-safe. Callable from the agent worker thread."""
        self._seq[run_id] = self._seq.get(run_id, 0) + 1
        event = Event(run_id=run_id, type=type_, payload=payload or {},
                      seq=self._seq[run_id])
        self._history.setdefault(run_id, []).append(event)

        for queue in list(self._queues.get(run_id, [])):
            if self._loop is not None and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(queue.put_nowait, event)
            else:
                queue.put_nowait(event)
        return event

    # -- consuming ---------------------------------------------------------

    async def subscribe(self, run_id: str) -> AsyncIterator[Event]:
        """Replays anything already emitted, then follows live.

        Replay matters: the browser subscribes a beat after POSTing the run,
        and without it the first few events are lost.
        """
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._queues.setdefault(run_id, []).append(queue)

        try:
            for past in list(self._history.get(run_id, [])):
                yield past
                if past.type in TERMINAL:
                    return

            while True:
                event = await queue.get()
                yield event
                if event.type in TERMINAL:
                    return
        finally:
            subs = self._queues.get(run_id, [])
            if queue in subs:
                subs.remove(queue)

    def history(self, run_id: str) -> list[Event]:
        return list(self._history.get(run_id, []))

    def forget(self, run_id: str) -> None:
        self._history.pop(run_id, None)
        self._queues.pop(run_id, None)
        self._seq.pop(run_id, None)


bus = EventBus()
