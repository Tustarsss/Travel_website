"""Facility discovery service using routing graph distances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.algorithms import WeightStrategy
from app.models.enums import FacilityCategory, TransportMode
from app.repositories import FacilityRepository, GraphRepository, RegionRepository
from app.services.routing import (
    NodeValidationError,
    RegionNotFoundError,
    RouteNotFoundError,
    RoutePlan,
    RoutingService,
)


@dataclass(slots=True)
class FacilityRoute:
    """Route metadata for a facility recommendation."""

    facility_id: int
    name: str
    category: FacilityCategory
    latitude: float
    longitude: float
    distance: float
    travel_time: float
    node_sequence: tuple[int, ...]
    strategy: WeightStrategy


class FacilityService:
    """High level facility discovery orchestrator."""

    def __init__(
        self,
        facility_repository: FacilityRepository,
        graph_repository: GraphRepository,
        region_repository: RegionRepository,
    ) -> None:
        self._facility_repository = facility_repository
        self._graph_repository = graph_repository
        self._region_repository = region_repository
        self._routing_service = RoutingService(graph_repository, region_repository)

    async def find_nearby_facilities(
        self,
        *,
        region_id: int,
        origin_node_id: int,
        radius_meters: float | None = 500.0,
        limit: int = 10,
        strategy: WeightStrategy | str = WeightStrategy.DISTANCE,
    categories: Sequence[FacilityCategory | str] | None = None,
    transport_modes: Sequence[TransportMode | str] | None = None,
    ) -> list[FacilityRoute]:
        """Return facilities reachable from an origin node ordered by travel metric."""

        region = await self._region_repository.get_region(region_id)
        if region is None:
            raise RegionNotFoundError(f"Region {region_id} does not exist")

        origin_node = await self._graph_repository.get_node(origin_node_id)
        if origin_node is None or origin_node.region_id != region_id:
            raise NodeValidationError("Origin node must exist within the specified region")

        parsed_categories: list[FacilityCategory] | None = None
        if categories:
            parsed_categories = [FacilityCategory(category) for category in categories]

        facility_nodes = await self._facility_repository.list_facilities_with_nodes(
            region_id,
            categories=parsed_categories,
        )
        if not facility_nodes:
            return []

        weight_strategy = WeightStrategy(strategy)

        results: list[FacilityRoute] = []
        for facility, node in facility_nodes:
            try:
                plan = await self._routing_service.compute_route(
                    region_id=region_id,
                    start_node_id=origin_node_id,
                    end_node_id=node.id,
                    strategy=weight_strategy,
                    transport_modes=transport_modes,
                )
            except RouteNotFoundError:
                continue

            if radius_meters is not None and plan.total_distance > radius_meters:
                continue

            results.append(
                FacilityRoute(
                    facility_id=facility.id,
                    name=facility.name,
                    category=facility.category,
                    latitude=facility.latitude,
                    longitude=facility.longitude,
                    distance=plan.total_distance,
                    travel_time=plan.total_time,
                    node_sequence=tuple(node.id for node in plan.nodes),
                    strategy=weight_strategy,
                )
            )

        if weight_strategy is WeightStrategy.DISTANCE:
            results.sort(key=lambda item: item.distance)
        else:
            results.sort(key=lambda item: item.travel_time)

        if limit > 0:
            results = results[:limit]

        return results
