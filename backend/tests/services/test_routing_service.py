"""Tests for the routing service."""

from __future__ import annotations

import pytest

from app.models.enums import RegionType, TransportMode
from app.models.graph import GraphEdge, GraphNode
from app.models.locations import Region
from app.services import (
    NodeValidationError,
    RegionNotFoundError,
    RouteNotFoundError,
    RoutingService,
)


class FakeGraphRepository:
    def __init__(self, nodes: dict[int, GraphNode], edges: list[GraphEdge]) -> None:
        self._nodes = nodes
        self._edges = edges

    async def get_node(self, node_id: int) -> GraphNode | None:
        return self._nodes.get(node_id)

    async def get_nodes(self, node_ids: list[int]) -> list[GraphNode]:
        return [self._nodes[node_id] for node_id in node_ids if node_id in self._nodes]

    async def list_edges_by_region(self, region_id: int) -> list[GraphEdge]:
        return [edge for edge in self._edges if edge.region_id == region_id]


class FakeRegionRepository:
    def __init__(self, regions: dict[int, Region]) -> None:
        self._regions = regions

    async def get_region(self, region_id: int) -> Region | None:
        return self._regions.get(region_id)


@pytest.fixture()
def sample_graph() -> tuple[FakeGraphRepository, FakeRegionRepository]:
    region = Region(
        id=1,
        name="测试景区",
        type=RegionType.SCENIC,
        popularity=80,
        rating=4.5,
    )

    nodes = {
        1: GraphNode(id=1, region_id=1, name="入口", latitude=0.0, longitude=0.0),
        2: GraphNode(id=2, region_id=1, name="湖心", latitude=0.0, longitude=1.0),
        3: GraphNode(id=3, region_id=1, name="终点", latitude=1.0, longitude=1.0),
    }

    edges = [
        GraphEdge(
            id=1,
            region_id=1,
            start_node_id=1,
            end_node_id=2,
            distance=100.0,
            ideal_speed=1.0,
            congestion=1.0,
            transport_modes=[TransportMode.WALK, TransportMode.ELECTRIC_CART],
        ),
        GraphEdge(
            id=2,
            region_id=1,
            start_node_id=2,
            end_node_id=3,
            distance=150.0,
            ideal_speed=1.5,
            congestion=1.0,
            transport_modes=[TransportMode.WALK, TransportMode.ELECTRIC_CART],
        ),
    ]

    return FakeGraphRepository(nodes, edges), FakeRegionRepository({1: region})


@pytest.mark.asyncio
async def test_compute_route_returns_path(sample_graph: tuple[FakeGraphRepository, FakeRegionRepository]) -> None:
    graph_repo, region_repo = sample_graph
    service = RoutingService(graph_repo, region_repo)

    plan = await service.compute_route(region_id=1, start_node_id=1, end_node_id=3)

    assert plan.total_distance == pytest.approx(250.0)
    assert plan.total_time == pytest.approx(100.0 / 1.0 + 150.0 / 1.5)
    assert [node.id for node in plan.nodes] == [1, 2, 3]
    assert [segment.transport_mode for segment in plan.segments] == ["walk", "walk"]
    assert set(plan.allowed_modes) == {"walk", "electric_cart"}


@pytest.mark.asyncio
async def test_compute_route_filters_transport_modes(sample_graph: tuple[FakeGraphRepository, FakeRegionRepository]) -> None:
    graph_repo, region_repo = sample_graph
    service = RoutingService(graph_repo, region_repo)

    plan = await service.compute_route(
        region_id=1,
        start_node_id=1,
        end_node_id=3,
        transport_modes=["electric_cart"],
    )

    assert [segment.transport_mode for segment in plan.segments] == ["electric_cart", "electric_cart"]


@pytest.mark.asyncio
async def test_compute_route_rejects_invalid_modes(sample_graph: tuple[FakeGraphRepository, FakeRegionRepository]) -> None:
    graph_repo, region_repo = sample_graph
    service = RoutingService(graph_repo, region_repo)

    with pytest.raises(NodeValidationError):
        await service.compute_route(
            region_id=1,
            start_node_id=1,
            end_node_id=3,
            transport_modes=["bike"],
        )


@pytest.mark.asyncio
async def test_compute_route_region_not_found(sample_graph: tuple[FakeGraphRepository, FakeRegionRepository]) -> None:
    graph_repo, region_repo = sample_graph
    service = RoutingService(graph_repo, region_repo)

    with pytest.raises(RegionNotFoundError):
        await service.compute_route(region_id=99, start_node_id=1, end_node_id=3)


@pytest.mark.asyncio
async def test_compute_route_missing_nodes(sample_graph: tuple[FakeGraphRepository, FakeRegionRepository]) -> None:
    graph_repo, region_repo = sample_graph
    service = RoutingService(graph_repo, region_repo)

    with pytest.raises(NodeValidationError):
        await service.compute_route(region_id=1, start_node_id=1, end_node_id=999)


@pytest.mark.asyncio
async def test_compute_route_no_path_raises(sample_graph: tuple[FakeGraphRepository, FakeRegionRepository]) -> None:
    graph_repo, region_repo = sample_graph
    service = RoutingService(graph_repo, region_repo)

    # Remove final edge to break connectivity
    graph_repo._edges = graph_repo._edges[:1]

    with pytest.raises(RouteNotFoundError):
        await service.compute_route(region_id=1, start_node_id=1, end_node_id=3)
