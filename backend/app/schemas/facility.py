"""Pydantic schemas for facility discovery responses."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.algorithms import WeightStrategy
from app.models.enums import FacilityCategory


class FacilityRouteItem(BaseModel):
    facility_id: int
    name: str
    category: FacilityCategory
    latitude: float
    longitude: float
    distance: float = Field(ge=0)
    travel_time: float = Field(ge=0)
    node_sequence: List[int]
    strategy: WeightStrategy

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("category")
    def _serialise_category(self, category: FacilityCategory) -> str:
        return category.value

    @field_serializer("strategy")
    def _serialise_strategy(self, strategy: WeightStrategy) -> str:
        return strategy.value


class FacilityRouteResponse(BaseModel):
    region_id: int
    origin_node_id: int
    radius_meters: float | None
    items: List[FacilityRouteItem]
    total: int

    model_config = ConfigDict(from_attributes=True)