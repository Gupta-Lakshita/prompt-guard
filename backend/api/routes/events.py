"""GET /events — retrieve logged scan events for the dashboard."""

from typing import List
from fastapi import APIRouter, Query

from backend.db.event_logger import get_events

router = APIRouter()


@router.get("/events")
def list_events(
    limit: int = Query(default=100, ge=1, le=500, description="Max events to return")
) -> List[dict]:
    """
    Return logged scan events, most recent first.

    Used by Raima's React dashboard to populate the security event log.
    Each event has the same shape as the ScanResponse contract.

    Query params:
        limit — number of events to return (1–500, default 100)
    """
    return get_events(limit=limit)
