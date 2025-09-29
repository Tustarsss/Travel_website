"""Map data endpoints serving GeoJSON tiles."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.api import deps
from app.schemas.map_data import MapTileSummary
from app.services.map_data import MapDataService, MapTileNotFoundError

router = APIRouter(prefix="/map-data", tags=["map-data"])


@router.get("/", response_model=List[MapTileSummary])
async def list_map_tiles(
    service: MapDataService = Depends(deps.get_map_data_service),
) -> List[MapTileSummary]:
    """List regions with available GeoJSON tiles."""

    return await service.list_tiles()


@router.get("/{region_id}", response_model=Dict[str, Any])
async def get_map_tile(
    region_id: int,
    service: MapDataService = Depends(deps.get_map_data_service),
) -> Dict[str, Any]:
    """Return the GeoJSON feature collection for a region."""

    try:
        return await service.load_tile(region_id)
    except MapTileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
