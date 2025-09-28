"""Pydantic schemas for routing endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.algorithms import WeightStrategy


class RouteNode(BaseModel):
    id: int
    name: str | None = None
    latitude: float
    longitude: float

    model_config = ConfigDict(from_attributes=True)


class RouteSegment(BaseModel):
    source_id: int
    target_id: int
    transport_mode: str = Field(description="Transport mode used between nodes", examples=["walk"])
    distance: float = Field(ge=0)
    time: float = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class RoutePlanResponse(BaseModel):
    region_id: int
    strategy: WeightStrategy
    total_distance: float = Field(ge=0)
    total_time: float = Field(ge=0)
    nodes: List[RouteNode]
    segments: List[RouteSegment]
    generated_at: datetime
    allowed_transport_modes: List[str]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("strategy")
    def _serialise_strategy(self, strategy: WeightStrategy) -> str:
        return strategy.value
