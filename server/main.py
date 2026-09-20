"""
server/main.py — FastAPI + WebSocket bridge for the PRAHARÍ React frontend.

Exposes the endpoints the frontend already calls:
    WS   /ws                     stream agent events
    GET  /security/status        honest security posture
    POST /security/egress-test   real outbound-reachability probe
    POST /task                    inspection | search workflow (multipart)
    POST /task/coding            coding workflow (multipart)
    GET  /artifacts/{filename}    download generated DOCX

Runs entirely on localhost. The heavy pipeline runs in a background thread and
streams events over the WebSocket. A single-flight lock guarantees only one
workflow runs at a time — this preserves NEBULA's one-model-at-a-time memory
safety on the 16 GB M4 (concurrent runs would load multiple models).
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional, Set

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from server import security
from server.coding_agent import run_coding_agent
from server.events import make
from server.runner import run_inspection, run_search

OUTPUT_DIR = Path(os.getenv("ARTIFACTS_OUTPUT_DIR", "./output"))

# Vite dev server (5173) + preview (4173), both localhost and 127.0.0.1.
ALLOWED_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:4173", "http://127.0.0.1:4173",
]

app = FastAPI(title="NEBULA / PRAHARÍ API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket broadcast manager ─────────────────────────────────────────────

class WSManager:
    """Tracks connected clients and broadcasts events (single-user demo)."""

    def __init__(self) -> None:
        self.connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.discard(ws)

    async def broadcast(self, event: dict) -> None:
        dead = []
        for ws in list(self.connections):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.discard(ws)


manager = WSManager()

# One workflow at a time (memory safety — one model loaded at a time).
_job_lock = threading.Lock()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            # Frontend doesn't send messages; this just keeps the socket open
            # and detects disconnects.
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


# ── Job dispatch ────────────────────────────────────────────────────────────

def _run_job(workflow: str, task: str, file_path: Optional[str],
             cleanup: Optional[str], loop: asyncio.AbstractEventLoop) -> None:
    """Background-thread entry point. Bridges emit() → WebSocket broadcast."""

    def emit(event: dict) -> None:
        future = asyncio.run_coroutine_threadsafe(manager.broadcast(event), loop)
        try:
            future.result(timeout=10)
        except Exception:
            pass

    try:
        if workflow == "coding":
            run_coding_agent(task, emit)
        elif workflow == "search":
            run_search(task, emit)
        else:
            # inspection: uploaded file (if any) is the report; SOP is server-side.
            run_inspection(task, file_path, None, emit)
    except Exception as exc:  # pragma: no cover - defensive
        emit(make("error", "complete", f"Unexpected server error: {exc}", {}))
    finally:
        if cleanup:
            try:
                os.unlink(cleanup)
            except Exception:
                pass
        _job_lock.release()


async def _dispatch(workflow: str, task: str, file: Optional[UploadFile]) -> JSONResponse:
    if not _job_lock.acquire(blocking=False):
        await manager.broadcast(make(
            "error", "complete",
            "A task is already running — please wait for it to finish.", {},
        ))
        return JSONResponse({"status": "busy"}, status_code=409)

    # Persist upload to a temp file (inspection workflow only).
    file_path: Optional[str] = None
    cleanup: Optional[str] = None
    try:
        if file is not None and workflow == "inspection":
            suffix = Path(file.filename or "upload.pdf").suffix or ".pdf"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="nebula_upload_") as tmp:
                tmp.write(await file.read())
                file_path = tmp.name
                cleanup = tmp.name
    except Exception as exc:
        _job_lock.release()
        return JSONResponse({"status": "error", "detail": f"upload failed: {exc}"}, status_code=400)

    loop = asyncio.get_running_loop()
    threading.Thread(
        target=_run_job, args=(workflow, task, file_path, cleanup, loop), daemon=True,
    ).start()
    return JSONResponse({"status": "started", "workflow": workflow})


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
def root() -> dict:
    return {"service": "NEBULA / PRAHARÍ API", "status": "ok", "mode": "LOCAL_ONLY"}


@app.get("/health")
async def health() -> dict:
    from core.health import check_ollama
    pf = await run_in_threadpool(check_ollama)
    return {
        "ollama_up": pf.ollama_up,
        "ready": pf.ready,
        "models_present": pf.models_present,
        "message": pf.message,
    }


@app.get("/security/status")
def security_status() -> dict:
    return security.get_status()


@app.post("/security/egress-test")
async def egress_test() -> dict:
    # Blocking socket probes → run off the event loop.
    return await run_in_threadpool(security.run_egress_test)


@app.post("/task")
async def task(
    task_description: str = Form(...),
    workflow: str = Form("inspection"),
    file: Optional[UploadFile] = File(None),
) -> JSONResponse:
    wf = workflow if workflow in ("inspection", "search") else "inspection"
    return await _dispatch(wf, task_description, file)


@app.post("/task/coding")
async def task_coding(
    task_description: str = Form(...),
    file: Optional[UploadFile] = File(None),
) -> JSONResponse:
    return await _dispatch("coding", task_description, None)


@app.get("/artifacts/{filename}")
def get_artifact(filename: str) -> FileResponse:
    safe = Path(filename).name  # prevent path traversal
    fp = OUTPUT_DIR / safe
    if not fp.exists() or not fp.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(
        str(fp),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe,
    )
