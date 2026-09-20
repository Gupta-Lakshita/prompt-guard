"""GET /health — simple liveness check."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Return 200 OK to confirm the backend is running."""
    return {"status": "ok"}
