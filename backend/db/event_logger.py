"""
Event logger — SQLite read/write operations for scan events.
"""

import json
from typing import List, Optional

from backend.db.database import get_connection


def insert_event(
    scan_id: str,
    original_prompt: str,
    sanitized_prompt: Optional[str],
    risk_score: int,
    decision: str,
    threats: List[str],
    signals: List[dict],
    pii: List[dict],
    timestamp: str,
) -> None:
    """
    Persist a single scan event to the SQLite events table.

    List fields (threats, signals, pii) are serialised to JSON strings
    before storage and deserialised back on retrieval by get_events().
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO events (
                scan_id, original_prompt, sanitized_prompt,
                risk_score, decision, threats, signals, pii, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                original_prompt,
                sanitized_prompt,
                risk_score,
                decision,
                json.dumps(threats),
                json.dumps(signals),
                json.dumps(pii),
                timestamp,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_events(limit: int = 100) -> List[dict]:
    """
    Retrieve logged scan events from SQLite, most recent first.

    List fields are deserialised from JSON strings back into Python lists
    so the API response is clean JSON.

    Args:
        limit: Maximum number of events to return (default 100).

    Returns:
        List of event dicts, newest first.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()

        events = []
        for row in rows:
            event = dict(row)
            event["threats"] = json.loads(event["threats"])
            event["signals"] = json.loads(event["signals"])
            event["pii"] = json.loads(event["pii"])
            events.append(event)

        return events
    finally:
        conn.close()
