"""Tests for the recommendation service."""

from __future__ import annotations

import pytest

from app.models.enums import RegionType
from app.models.locations import Region
from app.services import RecommendationService, RecommendationSort


class StubRegionRepository:
    def __init__(self, regions: list[Region]) -> None:
        self._regions = regions

    async def list_regions(self, *, region_type: RegionType | None = None) -> list[Region]:
        if region_type is None:
            return list(self._regions)
        return [region for region in self._regions if region.type == region_type]


@pytest.fixture()
def sample_regions() -> list[Region]:
    return [
        Region(
            id=1,
            name="杭州西湖景区",
            type=RegionType.SCENIC,
            popularity=90,
            rating=4.8,
            description="湖泊 自然 风景",
            city="杭州",
        ),
        Region(
            id=2,
            name="成都美食街",
            type=RegionType.SCENIC,
            popularity=70,
            rating=4.6,
            description="美食 文化 夜市",
            city="成都",
        ),
        Region(
            id=3,
            name="清华大学校园",
            type=RegionType.CAMPUS,
            popularity=65,
            rating=4.9,
            description="历史 科技 人文",
            city="北京",
        ),
    ]


@pytest.mark.asyncio
async def test_recommend_regions_orders_by_hybrid(sample_regions: list[Region]) -> None:
    service = RecommendationService(StubRegionRepository(sample_regions))

    result = await service.recommend_regions(limit=3)

    assert [item.region.id for item in result.items] == [1, 2, 3]
    assert result.sort_by is RecommendationSort.HYBRID
    assert result.total_candidates == 3


@pytest.mark.asyncio
async def test_recommend_regions_interest_boost(sample_regions: list[Region]) -> None:
    service = RecommendationService(StubRegionRepository(sample_regions))

    result = await service.recommend_regions(limit=2, interests=["美食"])

    assert any("美食" in item.interest_matches for item in result.items)
    assert result.items[0].region.id == 2  # boosted by interest match


@pytest.mark.asyncio
async def test_recommend_regions_search_filters(sample_regions: list[Region]) -> None:
    service = RecommendationService(StubRegionRepository(sample_regions))

    result = await service.recommend_regions(limit=5, search="历史")

    assert [item.region.id for item in result.items] == [3]
    assert result.total_candidates == 1


@pytest.mark.asyncio
async def test_recommend_regions_zero_limit(sample_regions: list[Region]) -> None:
    service = RecommendationService(StubRegionRepository(sample_regions))

    result = await service.recommend_regions(limit=0)

    assert result.items == []
    assert result.total_candidates == 0
