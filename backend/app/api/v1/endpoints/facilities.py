"""Facilities endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api import deps
from app.algorithms import WeightStrategy
from app.models.enums import FacilityCategory, TransportMode
from app.schemas import FacilityRouteItem, FacilityRouteResponse
from app.services import FacilityRoute, FacilityService, NodeValidationError, RegionNotFoundError

router = APIRouter(prefix="/facilities", tags=["facilities"])


@router.get("/nearby", response_model=FacilityRouteResponse)
async def list_nearby_facilities(
    *,
    region_id: int = Query(..., description="Region identifier"),
    origin_node_id: int = Query(..., description="Graph node representing the origin"),
    radius_meters: float | None = Query(500.0, ge=0, description="Maximum route distance to search"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of facilities to return"),
    strategy: WeightStrategy = Query(WeightStrategy.DISTANCE, description="Optimisation strategy"),
    categories: List[FacilityCategory] | None = Query(
        None, description="Optional facility categories to filter by", alias="category"
    ),
    transport_modes: List[TransportMode] | None = Query(
        None,
        description="Optional transport modes to restrict to (walk, bike, electric_cart)",
    ),
    service: FacilityService = Depends(deps.get_facility_service),
) -> FacilityRouteResponse:
    try:
        items = await service.find_nearby_facilities(
            region_id=region_id,
            origin_node_id=origin_node_id,
            radius_meters=radius_meters,
            limit=limit,
            strategy=strategy,
            categories=categories,
            transport_modes=transport_modes,
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NodeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FacilityRouteResponse(
        region_id=region_id,
        origin_node_id=origin_node_id,
        radius_meters=radius_meters,
        items=[FacilityRouteItem.model_validate(item) for item in items],
        total=len(items),
    )
