"""
Application configuration for Prompt Guard backend.

All tuneable values live here so nothing is hard-coded
throughout the application.
"""

import os
from typing import List

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Origins allowed to call the backend. Local dev defaults below always apply;
# set CORS_EXTRA_ORIGINS (comma-separated) to add the deployed frontend's
# origin (e.g. https://your-app.vercel.app) without touching this file.
_LOCAL_ORIGINS: List[str] = [
    "http://localhost:5173",   # Vite default
    "http://localhost:3000",   # CRA default
    "http://localhost:4173",   # Vite preview build
]
_extra = os.environ.get("CORS_EXTRA_ORIGINS", "")
CORS_ORIGINS: List[str] = _LOCAL_ORIGINS + [o.strip() for o in _extra.split(",") if o.strip()]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# SQLite file path. Defaults to the repo root for local dev; set DB_PATH to
# point at a mounted persistent disk in production (e.g. Render), otherwise
# logged events are lost on every redeploy/restart.
DB_PATH: str = os.environ.get("DB_PATH", "promptguard.db")

# ---------------------------------------------------------------------------
# Decision thresholds (risk_score is 0–100)
# ---------------------------------------------------------------------------
# 0  – ALLOW_MAX  → ALLOW
# ALLOW_MAX+1 – SANITIZE_MAX → SANITIZE
# SANITIZE_MAX+1 – 100 → BLOCK
THRESHOLD_ALLOW_MAX: int = 34    # 0–34   → ALLOW
THRESHOLD_SANITIZE_MAX: int = 69  # 35–69  → SANITIZE
                                   # 70–100 → BLOCK
