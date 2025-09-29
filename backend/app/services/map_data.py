"""Utilities to serve cached GeoJSON tiles for the map experience."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.locations import Region
from app.schemas.map_data import MapTileSummary

MAP_TILE_DIR = Path("indexes/map_tiles")
INDEX_FILE = MAP_TILE_DIR / "index.json"


class MapTileNotFoundError(Exception):
    """Raised when a GeoJSON tile for a region is unavailable."""


@dataclass
class _TileIndexEntry:
    region_id: int
    name: str
    tile: str
    updated_at: datetime | None


class MapDataService:
    """Provide metadata and GeoJSON payloads for the front-end map."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_tiles(self) -> List[MapTileSummary]:
        result = await self._session.exec(select(Region))
        regions = result.all()
        index = self._load_index()
        summaries: List[MapTileSummary] = []

        for region in regions:
            entry = index.get(region.id)
            tile_path = self._tile_path(region.id)
            summaries.append(
                MapTileSummary(
                    region_id=region.id,
                    name=region.name,
                    available=tile_path.exists(),
                    updated_at=entry.updated_at if entry else None,
                )
            )

        return summaries

    async def load_tile(self, region_id: int) -> Dict[str, Any]:
        if region_id <= 0:
            raise MapTileNotFoundError("Region id must be positive")

        tile_path = self._tile_path(region_id)
        if not tile_path.exists():
            raise MapTileNotFoundError(f"GeoJSON tile for region {region_id} not found")

        try:
            payload = json.loads(tile_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MapTileNotFoundError(f"Invalid GeoJSON payload for region {region_id}") from exc

        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            raise MapTileNotFoundError(f"GeoJSON tile for region {region_id} is malformed")

        return payload

    def _tile_path(self, region_id: int) -> Path:
        return MAP_TILE_DIR / f"region_{region_id}.geojson"

    def _load_index(self) -> Dict[int, _TileIndexEntry]:
        if not INDEX_FILE.exists():
            return {}

        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        entries: Dict[int, _TileIndexEntry] = {}
        for item in data.get("tiles", []):
            try:
                region_id = int(item["region_id"])
            except (KeyError, TypeError, ValueError):
                continue
            updated_at = None
            raw_timestamp = item.get("updated_at")
            if isinstance(raw_timestamp, str):
                try:
                    updated_at = datetime.fromisoformat(raw_timestamp)
                except ValueError:
                    updated_at = None
            entries[region_id] = _TileIndexEntry(
                region_id=region_id,
                name=str(item.get("name", "")),
                tile=str(item.get("tile", "")),
                updated_at=updated_at,
            )
        return entries


__all__ = ["MapDataService", "MapTileNotFoundError"]
