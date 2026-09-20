"""
conftest.py — ensures the repo root (prompt-guard/) is on sys.path
so both `backend` and `ai_ml` packages are importable when pytest
is run from any working directory.

Also initialises the SQLite events table before the test session starts,
because TestClient does not always trigger the FastAPI lifespan context.
"""

import sys
import os

# Navigate up from backend/tests/ → backend/ → prompt-guard/ (repo root)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Initialise the database so the events table exists before any test runs.
# This is safe to call multiple times (CREATE TABLE IF NOT EXISTS).
from backend.db.database import init_db  # noqa: E402
init_db()
