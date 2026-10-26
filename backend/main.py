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
from ai_ml import classifier, pii_detector


# ── Lifespan: one-time startup work ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise SQLite and warm up the ML/PII engines once on startup.

    Warming up here (rather than lazily on the first /scan request) matters
    on memory-constrained hosts: several requests arriving close together
    right after a cold start could otherwise each race past the lazy-init
    check and build their own ~130MB copy of the Presidio+spaCy engine
    concurrently, which is what caused repeated Render free-tier (512MB)
    OOMs. Building everything once here, single-threaded, before the app
    accepts traffic, makes that race impossible — at the cost of adding a
    few seconds to cold-start time, which is the right tradeoff here.
    """
    init_db()
    pii_detector.warm_up()
    classifier.warm_up()
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
