"""Tests for the facility service."""

from __future__ import annotations

import pytest

from app.algorithms import WeightStrategy
from app.models.enums import FacilityCategory, RegionType, TransportMode
from app.models.graph import GraphEdge, GraphNode
from app.models.locations import Facility, Region
from app.services import FacilityService, NodeValidationError, RegionNotFoundError


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


class FakeFacilityRepository:
    def __init__(self, mapping: dict[int, list[tuple[Facility, GraphNode]]]) -> None:
        self._mapping = mapping

    async def list_facilities_with_nodes(
        self,
        region_id: int,
        *,
        categories: list[FacilityCategory] | None = None,
    ) -> list[tuple[Facility, GraphNode]]:
        facilities = self._mapping.get(region_id, [])
        if categories:
            allowed = set(categories)
            return [(facility, node) for facility, node in facilities if facility.category in allowed]
        return list(facilities)


@pytest.fixture()
def facility_service() -> FacilityService:
    region = Region(
        id=1,
        name="测试景区",
        type=RegionType.SCENIC,
        popularity=80,
        rating=4.5,
    )

    nodes = {
        1: GraphNode(id=1, region_id=1, name="入口", latitude=0.0, longitude=0.0),
        2: GraphNode(id=2, region_id=1, name="餐厅节点", latitude=0.0, longitude=1.0, facility_id=101),
        3: GraphNode(id=3, region_id=1, name="洗手间节点", latitude=0.5, longitude=1.2, facility_id=102),
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
            transport_modes=[TransportMode.WALK],
        ),
        GraphEdge(
            id=2,
            region_id=1,
            start_node_id=2,
            end_node_id=3,
            distance=120.0,
            ideal_speed=1.0,
            congestion=1.0,
            transport_modes=[TransportMode.WALK],
        ),
    ]

    facilities = {
        1: [
            (
                Facility(
                    id=101,
                    region_id=1,
                    name="景区餐厅",
                    category=FacilityCategory.RESTAURANT,
                    latitude=0.0,
                    longitude=1.0,
                ),
                nodes[2],
            ),
            (
                Facility(
                    id=102,
                    region_id=1,
                    name="景区洗手间",
                    category=FacilityCategory.RESTROOM,
                    latitude=0.5,
                    longitude=1.2,
                ),
                nodes[3],
            ),
        ]
    }

    return FacilityService(
        FakeFacilityRepository(facilities),
        FakeGraphRepository(nodes, edges),
        FakeRegionRepository({1: region}),
    )


@pytest.mark.asyncio
async def test_find_nearby_facilities_orders_by_distance(facility_service: FacilityService) -> None:
    results = await facility_service.find_nearby_facilities(
        region_id=1,
        origin_node_id=1,
        radius_meters=500.0,
        limit=5,
        strategy=WeightStrategy.DISTANCE,
    )

    assert [item.facility_id for item in results] == [101, 102]
    assert results[0].distance < results[1].distance
    assert results[0].strategy is WeightStrategy.DISTANCE


@pytest.mark.asyncio
async def test_find_nearby_facilities_filters_by_radius(facility_service: FacilityService) -> None:
    results = await facility_service.find_nearby_facilities(
        region_id=1,
        origin_node_id=1,
        radius_meters=150.0,
        limit=5,
    )

    assert [item.facility_id for item in results] == [101]


@pytest.mark.asyncio
async def test_find_nearby_facilities_filters_by_category(facility_service: FacilityService) -> None:
    results = await facility_service.find_nearby_facilities(
        region_id=1,
        origin_node_id=1,
        categories=[FacilityCategory.RESTROOM],
    )

    assert [item.facility_id for item in results] == [102]


@pytest.mark.asyncio
async def test_find_nearby_facilities_raises_for_unknown_region(facility_service: FacilityService) -> None:
    with pytest.raises(RegionNotFoundError):
        await facility_service.find_nearby_facilities(region_id=99, origin_node_id=1)


@pytest.mark.asyncio
async def test_find_nearby_facilities_requires_origin_in_region(facility_service: FacilityService) -> None:
    with pytest.raises(NodeValidationError):
        await facility_service.find_nearby_facilities(region_id=1, origin_node_id=999)
