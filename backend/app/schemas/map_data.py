"""Schemas for map data endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MapTileSummary(BaseModel):
    """Metadata about an available GeoJSON tile."""

    region_id: int = Field(..., description="Region identifier")
    name: str = Field(..., description="Display name of the region")
    available: bool = Field(..., description="Whether the GeoJSON tile file exists")
    updated_at: datetime | None = Field(
        None, description="Timestamp of the last tile export in ISO format"
    )


__all__ = ["MapTileSummary"]
