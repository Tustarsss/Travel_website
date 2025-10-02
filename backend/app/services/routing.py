"""Routing service orchestrating shortest-path calculations."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Sequence
from collections import deque
import heapq

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
        # 缓存边数据和节点数据，避免重复加载
        self._edges_cache: dict[int, list] = {}
        self._nodes_cache: dict[int, GraphNode] = {}

    async def _get_edges_cached(self, region_id: int) -> list:
        """获取边数据（带缓存）。"""
        if region_id not in self._edges_cache:
            edges = await self._graph_repository.list_edges_by_region(region_id)
            self._edges_cache[region_id] = edges
        return self._edges_cache[region_id]
    
    async def _get_node_cached(self, node_id: int) -> GraphNode | None:
        """获取节点数据（带缓存）。"""
        if node_id not in self._nodes_cache:
            node = await self._graph_repository.get_node(node_id)
            if node:
                self._nodes_cache[node_id] = node
        return self._nodes_cache.get(node_id)

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

        # 使用缓存的边数据
        edges = await self._get_edges_cached(region_id)
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

    async def compute_reachable_nodes(
        self,
        *,
        region_id: int,
        origin_node_id: int,
        max_distance: float | None = None,
        strategy: WeightStrategy | str = WeightStrategy.DISTANCE,
        transport_modes: Sequence[TransportMode | str] | None = None,
    ) -> dict[int, dict[str, any]]:
        """
        使用 BFS 从起点计算所有可达节点的距离和路径。
        
        返回格式: {
            node_id: {
                "distance": float,  # 路径距离（米）
                "time": float,      # 旅行时间（分钟）
                "path": [node_ids], # 节点ID序列
            }
        }
        """
        region = await self._region_repository.get_region(region_id)
        if region is None:
            raise RegionNotFoundError(f"Region {region_id} does not exist")

        origin_node = await self._get_node_cached(origin_node_id)
        if origin_node is None or origin_node.region_id != region_id:
            raise NodeValidationError("Origin node must exist within the specified region")

        # 加载图数据
        edges = await self._get_edges_cached(region_id)
        if not edges:
            return {}

        allowed_modes = self._resolve_transport_modes(region.type, transport_modes)
        weight_strategy = WeightStrategy(strategy)

        # 构建邻接表
        graph: dict[int, list[tuple[int, float, float]]] = {}  # node_id -> [(neighbor_id, distance, time)]
        for edge in edges:
            # 检查交通方式是否允许
            edge_modes = set(edge.transport_modes or [])
            if not edge_modes.intersection(allowed_modes):
                continue

            distance = edge.distance
            time = distance / (edge.ideal_speed * edge.congestion / 60)  # 转换为分钟

            # 双向边
            if edge.start_node_id not in graph:
                graph[edge.start_node_id] = []
            if edge.end_node_id not in graph:
                graph[edge.end_node_id] = []
            
            graph[edge.start_node_id].append((edge.end_node_id, distance, time))
            graph[edge.end_node_id].append((edge.start_node_id, distance, time))

        # 使用 Dijkstra 算法进行遍历（优先队列确保最短路径）
        visited: dict[int, dict] = {}  # node_id -> {distance, time, path, parent}
        distances: dict[int, float] = {origin_node_id: 0.0}
        times: dict[int, float] = {origin_node_id: 0.0}
        parents: dict[int, int | None] = {origin_node_id: None}
        
        # 优先队列: (priority, node_id, distance, time)
        # priority 根据策略选择（距离或时间）
        if weight_strategy == WeightStrategy.DISTANCE:
            heap = [(0.0, origin_node_id, 0.0, 0.0)]
        else:
            heap = [(0.0, origin_node_id, 0.0, 0.0)]
        
        processed = set()

        while heap:
            priority, current_id, current_distance, current_time = heapq.heappop(heap)

            # 如果已处理过，跳过
            if current_id in processed:
                continue
            
            processed.add(current_id)

            # 检查距离限制
            if max_distance is not None and current_distance > max_distance:
                continue

            # 遍历邻居节点
            neighbors = graph.get(current_id, [])
            for neighbor_id, edge_distance, edge_time in neighbors:
                if neighbor_id in processed:
                    continue

                new_distance = current_distance + edge_distance
                new_time = current_time + edge_time

                # 检查是否找到更短路径
                if neighbor_id not in distances or new_distance < distances[neighbor_id]:
                    distances[neighbor_id] = new_distance
                    times[neighbor_id] = new_time
                    parents[neighbor_id] = current_id
                    
                    # 根据策略选择优先级
                    priority = new_distance if weight_strategy == WeightStrategy.DISTANCE else new_time
                    heapq.heappush(heap, (priority, neighbor_id, new_distance, new_time))

        # 重建路径
        for node_id in distances:
            if node_id == origin_node_id:
                visited[node_id] = {
                    "distance": 0.0,
                    "time": 0.0,
                    "path": [origin_node_id],
                }
            else:
                # 从父节点回溯构建路径
                path = []
                current = node_id
                while current is not None:
                    path.append(current)
                    current = parents.get(current)
                path.reverse()
                
                visited[node_id] = {
                    "distance": distances[node_id],
                    "time": times[node_id],
                    "path": path,
                }

        return visited

    async def _fetch_and_validate_nodes(
        self, region_id: int, start_node_id: int, end_node_id: int
    ) -> tuple[GraphNode, GraphNode]:
        # 使用缓存获取节点
        start_node = await self._get_node_cached(start_node_id)
        end_node = await self._get_node_cached(end_node_id)

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
        
        # 先从缓存中获取
        mapping = {}
        uncached_ids = []
        for node_id in unique_ids:
            cached_node = self._nodes_cache.get(node_id)
            if cached_node:
                mapping[node_id] = cached_node
            else:
                uncached_ids.append(node_id)
        
        # 批量获取未缓存的节点
        if uncached_ids:
            nodes = await self._graph_repository.get_nodes(sorted(uncached_ids))
            for node in nodes:
                mapping[node.id] = node
                self._nodes_cache[node.id] = node  # 缓存新获取的节点
        
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
