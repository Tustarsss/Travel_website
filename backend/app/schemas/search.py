"""Schemas for keyword search endpoints."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, field_serializer

from app.models.enums import RegionType


class RegionSearchResult(BaseModel):
	id: int
	name: str
	city: str | None = None
	type: RegionType | None = None
	keywords: List[str] | None = None
	description: str | None = None

	model_config = ConfigDict(from_attributes=True)

	@field_serializer("type")
	def _serialise_type(self, region_type: RegionType | None) -> str | None:
		return region_type.value if region_type else None


class RegionSearchResponse(BaseModel):
	items: List[RegionSearchResult]


class RegionNodeSummary(BaseModel):
	id: int
	name: str
	region_id: int
	code: str | None = None
	latitude: float | None = None
	longitude: float | None = None
	description: str | None = None

	model_config = ConfigDict(from_attributes=True)


class RegionNodeSearchResponse(BaseModel):
	items: List[RegionNodeSummary]
