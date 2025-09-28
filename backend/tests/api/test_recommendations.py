"""API tests for recommendation endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Generator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api import deps
from app.models.enums import RegionType
from app.models.locations import Region
from app.services import RecommendationResult, RecommendationSort, RegionRecommendation


class FakeRecommendationService:
    def __init__(self, result: RecommendationResult) -> None:
        self._result = result
        self.received_kwargs: Dict[str, Any] | None = None

    async def recommend_regions(self, **kwargs: Any) -> RecommendationResult:
        self.received_kwargs = kwargs
        return self._result


@pytest.fixture()
def recommendation_override(app: FastAPI) -> Generator[FakeRecommendationService, None, None]:
    region = Region(
        id=101,
        name="测试景区",
        type=RegionType.SCENIC,
        popularity=88,
        rating=4.5,
        description="美食 景观",
        city="杭州",
    )
    result = RecommendationResult(
        items=[
            RegionRecommendation(
                region=region,
                score=64.2,
                base_score=60.2,
                interest_matches=["美食"],
            )
        ],
        sort_by=RecommendationSort.HYBRID,
        generated_at=datetime.now(timezone.utc),
        total_candidates=1,
    )

    service = FakeRecommendationService(result)
    app.dependency_overrides[deps.get_recommendation_service] = lambda: service
    yield service
    app.dependency_overrides.pop(deps.get_recommendation_service, None)


@pytest.mark.asyncio
async def test_get_region_recommendations(async_client: AsyncClient, recommendation_override: FakeRecommendationService) -> None:
    response = await async_client.get(
        "/api/v1/recommendations/regions",
        params={"limit": 1, "interests": ["美食"], "q": "美食"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert payload["query"] == "美食"
    assert payload["items"][0]["region"]["name"] == "测试景区"
    assert payload["items"][0]["interest_matches"] == ["美食"]
    assert payload["items"][0]["base_score"] == pytest.approx(60.2)

    recorded = recommendation_override.received_kwargs
    assert recorded is not None
    assert recorded["limit"] == 1
    assert recorded["interests"] == ["美食"]
    assert recorded["search"] == "美食"