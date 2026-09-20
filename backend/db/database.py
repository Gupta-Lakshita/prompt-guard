"""
SQLite database connection and table initialisation.
"""

import sqlite3
from backend.core.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """
    Open and return a new SQLite connection.

    row_factory is set to sqlite3.Row so callers can access columns
    both by index and by name.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Create the events table if it does not already exist.
    Safe to call multiple times (idempotent).

    threats / signals / pii are stored as JSON strings because SQLite
    has no native array type. event_logger.py handles serialisation and
    deserialisation transparently.
    """
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                scan_id          TEXT PRIMARY KEY,
                original_prompt  TEXT NOT NULL,
                sanitized_prompt TEXT,
                risk_score       INTEGER NOT NULL,
                decision         TEXT NOT NULL,
                threats          TEXT NOT NULL,
                signals          TEXT NOT NULL,
                pii              TEXT NOT NULL,
                timestamp        TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()
