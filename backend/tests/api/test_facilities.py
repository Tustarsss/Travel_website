"""API tests for facility endpoints."""

from __future__ import annotations

from typing import Any, Dict, Generator, List

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api import deps
from app.algorithms import WeightStrategy
from app.models.enums import FacilityCategory, TransportMode
from app.services import FacilityRoute, FacilityService, NodeValidationError, RegionNotFoundError


class FakeFacilityService:
    def __init__(self, result: List[FacilityRoute] | None = None, error: Exception | None = None) -> None:
        self._result = result or []
        self._error = error
        self.received_kwargs: Dict[str, Any] | None = None

    async def find_nearby_facilities(self, **kwargs: Any) -> List[FacilityRoute]:
        self.received_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return self._result


@pytest.fixture()
def facility_override(app: FastAPI) -> Generator[FakeFacilityService, None, None]:
    result = [
        FacilityRoute(
            facility_id=101,
            name="景区餐厅",
            category=FacilityCategory.RESTAURANT,
            latitude=30.0,
            longitude=120.0,
            distance=120.0,
            travel_time=100.0,
            node_sequence=(1, 2),
            strategy=WeightStrategy.DISTANCE,
        )
    ]
    service = FakeFacilityService(result=result)
    app.dependency_overrides[deps.get_facility_service] = lambda: service
    yield service
    app.dependency_overrides.pop(deps.get_facility_service, None)


@pytest.mark.asyncio
async def test_list_nearby_facilities_success(async_client: AsyncClient, facility_override: FakeFacilityService) -> None:
    response = await async_client.get(
        "/api/v1/facilities/nearby",
        params={
            "region_id": 7,
            "origin_node_id": 1,
            "radius_meters": 400,
            "limit": 5,
            "strategy": WeightStrategy.DISTANCE.value,
            "category": [FacilityCategory.RESTAURANT.value],
            "transport_modes": [TransportMode.WALK.value],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["region_id"] == 7
    assert payload["origin_node_id"] == 1
    assert payload["total"] == 1
    assert payload["items"][0]["facility_id"] == 101
    assert payload["items"][0]["category"] == FacilityCategory.RESTAURANT.value
    assert payload["items"][0]["node_sequence"] == [1, 2]

    recorded = facility_override.received_kwargs
    assert recorded is not None
    assert recorded["region_id"] == 7
    assert recorded["origin_node_id"] == 1
    assert recorded["radius_meters"] == 400
    assert recorded["limit"] == 5
    assert recorded["strategy"] == WeightStrategy.DISTANCE
    assert recorded["categories"] == [FacilityCategory.RESTAURANT]
    assert recorded["transport_modes"] == [TransportMode.WALK]


@pytest.mark.asyncio
async def test_list_nearby_facilities_not_found(async_client: AsyncClient, app: FastAPI) -> None:
    service = FakeFacilityService(error=RegionNotFoundError("Region missing"))
    app.dependency_overrides[deps.get_facility_service] = lambda: service

    try:
        response = await async_client.get(
            "/api/v1/facilities/nearby",
            params={"region_id": 99, "origin_node_id": 1},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(deps.get_facility_service, None)


@pytest.mark.asyncio
async def test_list_nearby_facilities_node_error(async_client: AsyncClient, app: FastAPI) -> None:
    service = FakeFacilityService(error=NodeValidationError("bad origin"))
    app.dependency_overrides[deps.get_facility_service] = lambda: service

    try:
        response = await async_client.get(
            "/api/v1/facilities/nearby",
            params={"region_id": 1, "origin_node_id": 0},
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.pop(deps.get_facility_service, None)
