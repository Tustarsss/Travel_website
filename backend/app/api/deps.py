"""Reusable dependencies for API routes."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user as _current_active_user, fastapi_users
from app.models.users import User
from app.repositories import FacilityRepository, GraphRepository, RegionRepository
from app.repositories.diaries import DiaryRepository
from app.repositories.session import get_session
from app.repositories.users import UserRepository
from app.services import FacilityService, RecommendationService, RoutingService, SearchService
from app.services.diary import DiaryService
from app.services.map_data import MapDataService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an application-scoped async database session."""

    async with get_session() as session:
        yield session


async def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    """Provide a user repository instance."""

    return UserRepository(session)




async def get_recommendation_service(
    session: AsyncSession = Depends(get_db_session),
) -> RecommendationService:
    """Provide a :class:`~app.services.recommendation.RecommendationService` instance."""

    repository = RegionRepository(session)
    return RecommendationService(repository)


async def get_routing_service(
    session: AsyncSession = Depends(get_db_session),
) -> RoutingService:
    """Provide a :class:`~app.services.routing.RoutingService` instance."""

    graph_repository = GraphRepository(session)
    region_repository = RegionRepository(session)
    return RoutingService(graph_repository, region_repository)


async def get_facility_service(
    session: AsyncSession = Depends(get_db_session),
) -> FacilityService:
    """Provide a :class:`~app.services.facility.FacilityService` instance."""

    facility_repository = FacilityRepository(session)
    graph_repository = GraphRepository(session)
    region_repository = RegionRepository(session)
    return FacilityService(facility_repository, graph_repository, region_repository)


async def get_map_data_service(
    session: AsyncSession = Depends(get_db_session),
) -> MapDataService:
    """Provide a :class:`~app.services.map_data.MapDataService` instance."""

    return MapDataService(session)


async def get_search_service(
    session: AsyncSession = Depends(get_db_session),
) -> SearchService:
    """Provide a :class:`~app.services.search.SearchService` instance."""

    region_repository = RegionRepository(session)
    graph_repository = GraphRepository(session)
    return SearchService(region_repository, graph_repository)


async def get_diary_service(
    session: AsyncSession = Depends(get_db_session),
) -> DiaryService:
    """Provide a :class:`~app.services.diary.DiaryService` instance."""

    diary_repository = DiaryRepository(session)
    return DiaryService(diary_repository)


async def get_current_user(user: User = Depends(_current_active_user)) -> User:
    """Resolve the currently authenticated user via fastapi-users."""
    return user


async def get_optional_current_user(user: Optional[User] = Depends(fastapi_users.current_user(optional=True))):
    """Return the current user if available, else ``None`` using fastapi-users."""
    return user


__all__ = [
    "get_db_session",
    "get_user_repository",
    "get_recommendation_service",
    "get_routing_service",
    "get_facility_service",
    "get_map_data_service",
    "get_search_service",
    "get_diary_service",
    "get_current_user",
    "get_optional_current_user",
]
