"""
Application configuration for Prompt Guard backend.

All tuneable values live here so nothing is hard-coded
throughout the application.
"""

from typing import List

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Origins allowed to call the backend during local development.
# Raima's React/Vite app defaults to localhost:5173; CRA defaults to 3000.
# Update this list if the frontend port changes.
CORS_ORIGINS: List[str] = [
    "http://localhost:5173",   # Vite default
    "http://localhost:3000",   # CRA default
    "http://localhost:4173",   # Vite preview build
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# SQLite file path, relative to the working directory (repo root).
DB_PATH: str = "promptguard.db"

# ---------------------------------------------------------------------------
# Decision thresholds (risk_score is 0–100)
# ---------------------------------------------------------------------------
# 0  – ALLOW_MAX  → ALLOW
# ALLOW_MAX+1 – SANITIZE_MAX → SANITIZE
# SANITIZE_MAX+1 – 100 → BLOCK
THRESHOLD_ALLOW_MAX: int = 34    # 0–34   → ALLOW
THRESHOLD_SANITIZE_MAX: int = 69  # 35–69  → SANITIZE
                                   # 70–100 → BLOCK
