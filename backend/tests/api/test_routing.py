"""API tests for routing endpoints."""

from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api import deps
from app.algorithms import WeightStrategy
from app.services import (
    NodeValidationError,
    RegionNotFoundError,
    RouteNode,
    RouteNotFoundError,
    RoutePlan,
    RouteSegment,
)


class FakeRoutingService:
    def __init__(self, plan: RoutePlan | None = None, error: Exception | None = None) -> None:
        self._plan = plan
        self._error = error
        self.received_kwargs: Dict[str, Any] | None = None

    async def compute_route(self, **kwargs: Any) -> RoutePlan:
        self.received_kwargs = kwargs
        if self._error is not None:
            raise self._error
        if self._plan is None:
            raise RuntimeError("No plan configured for FakeRoutingService")
        return self._plan


@pytest.fixture()
def route_plan() -> RoutePlan:
    nodes = [
        RouteNode(id=1, name="入口", latitude=0.0, longitude=0.0),
        RouteNode(id=2, name="景点A", latitude=0.5, longitude=0.5),
    ]
    segments = [
        RouteSegment(source_id=1, target_id=2, transport_mode="walk", distance=120.0, time=100.0),
    ]
    return RoutePlan(
        region_id=7,
        strategy=WeightStrategy.TIME,
        total_distance=120.0,
        total_time=100.0,
        allowed_modes=("walk", "electric_cart"),
        nodes=nodes,
        segments=segments,
    )


@pytest.mark.asyncio
async def test_compute_route_success(app: FastAPI, async_client: AsyncClient, route_plan: RoutePlan) -> None:
    service = FakeRoutingService(plan=route_plan)
    app.dependency_overrides[deps.get_routing_service] = lambda: service

    try:
        response = await async_client.get(
            "/api/v1/routing/routes",
            params={
                "region_id": 7,
                "start_node_id": 1,
                "end_node_id": 2,
                "strategy": WeightStrategy.DISTANCE.value,
                "transport_modes": ["walk"],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["region_id"] == 7
        assert payload["strategy"] == WeightStrategy.TIME.value  # plan strategy wins
        assert sorted(payload["allowed_transport_modes"]) == ["electric_cart", "walk"]
        assert payload["nodes"][0]["name"] == "入口"
        assert payload["segments"][0]["transport_mode"] == "walk"

        recorded = service.received_kwargs
        assert recorded is not None
        assert recorded["region_id"] == 7
        assert recorded["start_node_id"] == 1
        assert recorded["end_node_id"] == 2
        assert recorded["strategy"] == WeightStrategy.DISTANCE.value
        assert recorded["transport_modes"] == ["walk"]
    finally:
        app.dependency_overrides.pop(deps.get_routing_service, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error, expected_status",
    [
        (RegionNotFoundError("missing"), 404),
        (NodeValidationError("bad nodes"), 400),
        (RouteNotFoundError("no path"), 404),
    ],
)
async def test_compute_route_errors(
    app: FastAPI,
    async_client: AsyncClient,
    error: Exception,
    expected_status: int,
) -> None:
    service = FakeRoutingService(error=error)
    app.dependency_overrides[deps.get_routing_service] = lambda: service

    try:
        response = await async_client.get(
            "/api/v1/routing/routes",
            params={"region_id": 7, "start_node_id": 1, "end_node_id": 2},
        )

        assert response.status_code == expected_status
    finally:
        app.dependency_overrides.pop(deps.get_routing_service, None)
