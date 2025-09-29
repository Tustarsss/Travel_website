"""Utilities to adapt raw OSM payloads into domain-friendly structures."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app.models.enums import BuildingCategory, FacilityCategory, RegionType

from .map_crawler import (
    convert_osm_buildings_to_model,
    convert_osm_pois_to_facilities,
)


class RealDataUnavailableError(RuntimeError):
    """Raised when required real-world map data cannot be assembled."""

    def __init__(self, message: str, *, location: str | None = None) -> None:
        self.location = location
        if location:
            super().__init__(f"[{location}] {message}")
        else:
            super().__init__(message)


@dataclass
class AdaptedRegionData:
    """Normalized collections derived from an OSM payload."""

    buildings: List[dict]
    facilities: List[dict]


def adapt_osm_payload(
    osm_payload: Optional[Dict],
    region_id: int,
    region_type: RegionType,
    min_buildings: int,
    min_facilities: int,
    *,
    location: str | None = None,
) -> AdaptedRegionData:
    """Map an optional OSM payload to domain collections with minimum counts ensured."""

    if osm_payload is None:
        raise RealDataUnavailableError("未获取到 OSM 数据。", location=location)

    buildings = convert_osm_buildings_to_model(osm_payload.get("buildings"), region_id)
    facilities = convert_osm_pois_to_facilities(osm_payload.get("pois"), region_id)

    if not buildings:
        raise RealDataUnavailableError("OSM 数据缺少可用的建筑要素。", location=location)

    if not facilities:
        raise RealDataUnavailableError("OSM 数据缺少可用的设施要素。", location=location)

    if len(buildings) < min_buildings:
        raise RealDataUnavailableError(
            f"建筑数量不足：需要至少 {min_buildings} 个，实际仅 {len(buildings)} 个。",
            location=location,
        )

    if len(facilities) < min_facilities:
        raise RealDataUnavailableError(
            f"设施数量不足：需要至少 {min_facilities} 个，实际仅 {len(facilities)} 个。",
            location=location,
        )

    return AdaptedRegionData(buildings=buildings, facilities=facilities)
