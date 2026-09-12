"""FastAPI application entrypoint.

Binds to 127.0.0.1 only. The one HTTP client in the process talks to Ollama on
loopback; nothing else in this application opens a socket outward.
"""

from __future__ import annotations

import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.document_routes import router as document_router
from .api.routes import router as api_router
from .config import ensure_dirs, get_settings
from .events import bus

# Belt and braces: make the ML ecosystem's implicit network calls impossible
# before any of it is imported.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("OLLAMA_HOST", "127.0.0.1:11434")

app = FastAPI(
    title="PRAHARI",
    description="Sovereign on-premise agentic AI workbench",
    version="0.1.0",
)

# The Next.js dev server is the only origin; in production the UI is served
# from this same process, so this list stays local either way.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(document_router)


@app.on_event("startup")
async def on_startup() -> None:
    ensure_dirs()
    bus.bind_loop(asyncio.get_running_loop())
    settings = get_settings()
    print(f"[PRAHARI] profile={settings.profile.name} "
          f"({settings.profile.label}) budget={settings.profile.budget_mb} MB")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "PRAHARI",
        "tagline": "AI comes to your data - not the other way around",
        "docs": "/docs",
        "health": "/api/health",
    }
