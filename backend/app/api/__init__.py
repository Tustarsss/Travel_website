"""API layer for versioned route registration."""

from fastapi import APIRouter

from .v1.router import api_router as v1_router

__all__ = ["get_api_router"]


def get_api_router() -> APIRouter:
    """Build the root API router with all versioned sub-routers."""
    router = APIRouter()
    router.include_router(v1_router, prefix="/v1")
    return router
