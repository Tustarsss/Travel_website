"""Reusable dependencies for API routes."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import FacilityRepository, GraphRepository, RegionRepository
from app.repositories.session import get_session
from app.services import FacilityService, RecommendationService, RoutingService, SearchService
from app.services.map_data import MapDataService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
	"""Yield an application-scoped async database session."""

	async with get_session() as session:
		yield session


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


__all__ = [
	"get_db_session",
	"get_recommendation_service",
	"get_routing_service",
	"get_facility_service",
	"get_map_data_service",
	"get_search_service",
]
