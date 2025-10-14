"""Reusable dependencies for API routes."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token, TokenValidationError
from app.models.users import User
from app.repositories import FacilityRepository, GraphRepository, RegionRepository
from app.repositories.diaries import DiaryRepository
from app.repositories.session import get_session
from app.repositories.users import UserRepository, UserSessionRepository
from app.services import FacilityService, RecommendationService, RoutingService, SearchService
from app.services.auth import AuthService
from app.services.diary import DiaryService
from app.services.map_data import MapDataService


_auth_scheme = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an application-scoped async database session."""

    async with get_session() as session:
        yield session


async def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    """Provide a user repository instance."""

    return UserRepository(session)


async def get_user_session_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserSessionRepository:
    """Provide a user session repository instance."""

    return UserSessionRepository(session)


async def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
) -> AuthService:
    """Construct an auth service bound to current session."""

    user_repo = UserRepository(session)
    session_repo = UserSessionRepository(session)
    return AuthService(user_repo, session_repo)


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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_auth_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Resolve the currently authenticated user."""

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证用户")

    try:
        token_data = decode_token(credentials.credentials, expected_type="access")
    except TokenValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    try:
        user_id = int(token_data.subject)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效") from exc

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")

    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_auth_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """Return the current user if available, else ``None``."""

    if credentials is None:
        return None

    try:
        token_data = decode_token(credentials.credentials, expected_type="access")
    except TokenValidationError:
        return None

    try:
        user_id = int(token_data.subject)
    except ValueError:
        return None

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        return None

    return user


__all__ = [
    "get_db_session",
    "get_user_repository",
    "get_user_session_repository",
    "get_auth_service",
    "get_recommendation_service",
    "get_routing_service",
    "get_facility_service",
    "get_map_data_service",
    "get_search_service",
    "get_diary_service",
    "get_current_user",
    "get_optional_current_user",
]
