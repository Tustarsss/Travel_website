"""Version 1 API router definition."""

from fastapi import APIRouter

from .endpoints import facilities, health, recommendations, routing

api_router = APIRouter(prefix="", tags=["v1"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(recommendations.router)
api_router.include_router(routing.router)
api_router.include_router(facilities.router)
