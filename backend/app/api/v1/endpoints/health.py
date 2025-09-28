"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("", summary="Health status", response_model=dict)
async def read_health() -> dict[str, str]:
    """Return service health metadata."""
    return {"status": "ok"}
