"""Recommendation endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from app.api import deps
from app.models.locations import RegionType
from app.schemas import RegionRecommendationItem, RegionRecommendationResponse, RegionSummary
from app.services import RecommendationService, RecommendationSort

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/regions", response_model=RegionRecommendationResponse)
async def recommend_regions(
    *,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of items to return"),
    sort_by: RecommendationSort = Query(RecommendationSort.HYBRID, description="Sorting strategy"),
    interests: List[str] = Query(default_factory=list, description="Interest tags to boost matches"),
    interests_only: bool = Query(False, description="When true, only include regions that match at least one interest tag"),
    q: str | None = Query(None, description="Full-text search query"),
    region_type: RegionType | None = Query(None, description="Filter by region type"),
    service: RecommendationService = Depends(deps.get_recommendation_service),
) -> RegionRecommendationResponse:
    """Return personalised region recommendations."""

    result = await service.recommend_regions(
        limit=limit,
        sort_by=sort_by,
        interests=interests,
        search=q,
        region_type=region_type,
        interests_only=interests_only,
    )

    items = [
        RegionRecommendationItem(
            region=RegionSummary.model_validate(rec.region),
            score=rec.score,
            base_score=rec.base_score,
            interest_matches=rec.interest_matches,
        )
        for rec in result.items
    ]

    return RegionRecommendationResponse(
        items=items,
        sort_by=result.sort_by,
        generated_at=result.generated_at,
        limit=limit,
        total_candidates=result.total_candidates,
        query=q,
        interests=interests,
    )
