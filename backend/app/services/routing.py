"""Routing service orchestrating shortest-path calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from app.algorithms import Edge as AlgoEdge
from app.algorithms import PathResult, PathSegment as AlgoPathSegment, WeightStrategy, shortest_path
from app.models.enums import RegionType, TransportMode
from app.models.graph import GraphEdge, GraphNode
from app.repositories import GraphRepository, RegionRepository


@dataclass(slots=True)
class RouteNode:
    id: int
    name: str | None
    latitude: float
    longitude: float


@dataclass(slots=True)
class RouteSegment:
    source_id: int
    target_id: int
    transport_mode: str
    distance: float
    time: float


@dataclass(slots=True)
class RoutePlan:
    region_id: int
    strategy: WeightStrategy
    total_distance: float
    total_time: float
    allowed_modes: tuple[str, ...]
    nodes: list[RouteNode]
    segments: list[RouteSegment]


class RoutingError(Exception):
    """Base exception for routing failures."""


class RegionNotFoundError(RoutingError):
    """Raised when the requested region does not exist."""


class NodeValidationError(RoutingError):
    """Raised when nodes are missing or do not belong to the region."""


class RouteNotFoundError(RoutingError):
    """Raised when no route could be computed between nodes."""


class RoutingService:
    """High-level service combining repositories and shortest-path algorithm."""

    def __init__(self, graph_repository: GraphRepository, region_repository: RegionRepository) -> None:
        self._graph_repository = graph_repository
        self._region_repository = region_repository

    async def compute_route(
        self,
        *,
        region_id: int,
        start_node_id: int,
        end_node_id: int,
        strategy: WeightStrategy | str = WeightStrategy.TIME,
        transport_modes: Sequence[TransportMode | str] | None = None,
    ) -> RoutePlan:
        region = await self._region_repository.get_region(region_id)
        if region is None:
            raise RegionNotFoundError(f"Region {region_id} does not exist")

        start_node, end_node = await self._fetch_and_validate_nodes(region_id, start_node_id, end_node_id)

        edges = await self._graph_repository.list_edges_by_region(region_id)
        if not edges:
            raise RouteNotFoundError(f"Region {region_id} has no routing edges")

        algorithm_edges = self._to_algorithm_edges(edges)
        allowed_modes = self._resolve_transport_modes(region.type, transport_modes)

        try:
            result = shortest_path(
                algorithm_edges,
                start=str(start_node_id),
                goal=str(end_node_id),
                allowed_modes=allowed_modes,
                strategy=strategy,
            )
        except ValueError as exc:  # from algorithm when no path or invalid graph
            raise RouteNotFoundError(str(exc)) from exc

        node_map = await self._build_node_map(region_id, result.nodes)
        route_nodes = [self._to_route_node(node_map, node_id) for node_id in result.nodes]
        route_segments = [self._to_route_segment(node_map, segment) for segment in result.segments]

        return RoutePlan(
            region_id=region_id,
            strategy=WeightStrategy(strategy),
            total_distance=result.total_distance,
            total_time=result.total_time,
            allowed_modes=tuple(allowed_modes),
            nodes=route_nodes,
            segments=route_segments,
        )

    async def _fetch_and_validate_nodes(
        self, region_id: int, start_node_id: int, end_node_id: int
    ) -> tuple[GraphNode, GraphNode]:
        start_node = await self._graph_repository.get_node(start_node_id)
        end_node = await self._graph_repository.get_node(end_node_id)

        if start_node is None or end_node is None:
            missing = []
            if start_node is None:
                missing.append(str(start_node_id))
            if end_node is None:
                missing.append(str(end_node_id))
            raise NodeValidationError(f"Nodes not found: {', '.join(missing)}")

        if start_node.region_id != region_id or end_node.region_id != region_id:
            raise NodeValidationError("Nodes must belong to the specified region")

        return start_node, end_node

    async def _build_node_map(self, region_id: int, node_ids: Iterable[str]) -> dict[int, GraphNode]:
        unique_ids = {int(node_id) for node_id in node_ids}
        nodes = await self._graph_repository.get_nodes(sorted(unique_ids))
        mapping = {node.id: node for node in nodes}
        if len(mapping) != len(unique_ids):
            missing = unique_ids - mapping.keys()
            raise NodeValidationError(f"Missing nodes in region {region_id}: {sorted(missing)}")
        return mapping

    def _to_route_node(self, node_map: dict[int, GraphNode], node_id: str) -> RouteNode:
        identifier = int(node_id)
        node = node_map.get(identifier)
        if node is None:
            raise NodeValidationError(f"Node {identifier} not found in node map")
        return RouteNode(
            id=identifier,
            name=node.name,
            latitude=node.latitude,
            longitude=node.longitude,
        )

    def _to_route_segment(self, node_map: dict[int, GraphNode], segment: AlgoPathSegment) -> RouteSegment:
        source_id = int(segment.source)
        target_id = int(segment.target)
        if source_id not in node_map or target_id not in node_map:
            raise NodeValidationError("Segment references unknown nodes")
        return RouteSegment(
            source_id=source_id,
            target_id=target_id,
            transport_mode=segment.transport_mode,
            distance=segment.distance,
            time=segment.time,
        )

    def _to_algorithm_edges(self, edges: Sequence[GraphEdge]) -> list[AlgoEdge]:
        return [
            AlgoEdge(
                source=str(edge.start_node_id),
                target=str(edge.end_node_id),
                distance=edge.distance,
                ideal_speed=edge.ideal_speed,
                congestion=edge.congestion,
                transport_modes=self._normalise_modes(edge.transport_modes),
            )
            for edge in edges
        ]

    def _resolve_transport_modes(
        self,
        region_type: RegionType,
        transport_modes: Sequence[TransportMode | str] | None,
    ) -> Sequence[str] | None:
        defaults = self._default_modes(region_type)
        if transport_modes is None:
            return tuple(sorted(defaults))

        requested = {self._normalise_mode(mode) for mode in transport_modes}
        if not requested:
            return tuple(sorted(defaults))

        filtered = requested & defaults
        if not filtered:
            raise NodeValidationError("Provided transport modes are not allowed in this region")
        return tuple(sorted(filtered))

    def _default_modes(self, region_type: RegionType) -> set[str]:
        if region_type is RegionType.CAMPUS:
            return {TransportMode.WALK.value, TransportMode.BIKE.value}
        if region_type is RegionType.SCENIC:
            return {TransportMode.WALK.value, TransportMode.ELECTRIC_CART.value}
        return {TransportMode.WALK.value}

    def _normalise_modes(self, modes: Iterable[TransportMode | str]) -> tuple[str, ...]:
        return tuple(self._normalise_mode(mode) for mode in modes)

    def _normalise_mode(self, mode: TransportMode | str) -> str:
        if isinstance(mode, TransportMode):
            return mode.value
        return str(mode).lower()
