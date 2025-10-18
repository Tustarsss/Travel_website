"""Version 1 API router definition."""

from fastapi import APIRouter

from .endpoints import diaries, facilities, health, map_data, recommendations, routing, search
from .users_fastapi_users import router as users_router

api_router = APIRouter(prefix="", tags=["v1"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(users_router)
api_router.include_router(recommendations.router)
api_router.include_router(routing.router)
api_router.include_router(facilities.router)
api_router.include_router(map_data.router)
api_router.include_router(search.router)
api_router.include_router(diaries.router)
