"""Pydantic schemas for recommendation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from app.models.locations import RegionType
from app.services import RecommendationSort


class RegionSummary(BaseModel):
    """Lightweight region representation for API responses."""

    id: int
    name: str
    type: RegionType
    popularity: int
    rating: float
    city: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class RegionRecommendationItem(BaseModel):
    """Single recommended region with scores and matches."""

    region: RegionSummary
    score: float = Field(ge=0)
    base_score: float = Field(ge=0)
    interest_matches: List[str]


class RegionRecommendationResponse(BaseModel):
    """Envelope for recommendation responses with metadata."""

    items: List[RegionRecommendationItem]
    sort_by: RecommendationSort
    generated_at: datetime
    limit: int
    total_candidates: int
    query: str | None = None
    interests: List[str] = Field(default_factory=list)
    data_source: str = Field(default="database", description="Source of recommendation data")
