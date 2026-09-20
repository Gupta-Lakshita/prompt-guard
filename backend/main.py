"""
Prompt Guard — FastAPI application entry point.

Start the server with:
    uvicorn backend.main:app --reload --port 8000

The server must be started from the repo root (prompt-guard/) so that
the ai_ml package is on the Python path.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import CORS_ORIGINS
from backend.db.database import init_db
from backend.api.routes import scan, health, events


# ── Lifespan: initialise the database once on startup ───────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise SQLite on startup; nothing to clean up on shutdown."""
    init_db()
    yield


# ── Application ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Prompt Guard API",
    description=(
        "Security gateway for LLM prompt scanning. "
        "Detects injection, jailbreak, and PII. "
        "Returns ALLOW / SANITIZE / BLOCK decisions."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allows Raima's React/Vite frontend to call the backend during local dev.
# Origins are configured in backend/core/config.py — update there if the
# frontend port changes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────────────
app.include_router(scan.router)      # POST /scan
app.include_router(health.router)    # GET  /health
app.include_router(events.router)    # GET  /events
