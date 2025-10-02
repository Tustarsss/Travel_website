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

        # 使用 BFS 一次性计算从起点到所有可达节点的距离和路径
        # 这比为每个设施单独计算路径高效得多
        reachable_paths = await self._routing_service.compute_reachable_nodes(
            region_id=region_id,
            origin_node_id=origin_node_id,
            max_distance=radius_meters,
            strategy=weight_strategy,
            transport_modes=transport_modes,
        )

        # 构建设施节点ID到设施的映射
        facility_by_node_id = {node.id: facility for facility, node in facility_nodes}

        # 提取在可达范围内的设施
        results: list[FacilityRoute] = []
        for node_id, path_info in reachable_paths.items():
            facility = facility_by_node_id.get(node_id)
            if facility is None:
                continue

            results.append(
                FacilityRoute(
                    facility_id=facility.id,
                    name=facility.name,
                    category=facility.category,
                    latitude=facility.latitude,
                    longitude=facility.longitude,
                    distance=path_info["distance"],
                    travel_time=path_info["time"],
                    node_sequence=tuple(path_info["path"]),
                    strategy=weight_strategy,
                )
            )

        # 排序
        if weight_strategy is WeightStrategy.DISTANCE:
            results.sort(key=lambda item: item.distance)
        else:
            results.sort(key=lambda item: item.travel_time)

        # 限制返回数量
        if limit > 0:
            results = results[:limit]

        return results
