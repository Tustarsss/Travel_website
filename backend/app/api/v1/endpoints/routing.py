"""Routing endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api import deps
from app.algorithms import WeightStrategy
from app.services import NodeValidationError, RegionNotFoundError, RouteNotFoundError, RoutingService
from app.schemas import RoutePlanResponse, RouteSegment, RouteNode

router = APIRouter(prefix="/routing", tags=["routing"])


@router.get("/routes", response_model=RoutePlanResponse)
async def compute_route(
    *,
    region_id: int = Query(..., description="Region identifier containing the graph"),
    start_node_id: int = Query(..., description="Starting graph node identifier"),
    end_node_id: int = Query(..., description="Destination graph node identifier"),
    strategy: WeightStrategy = Query(WeightStrategy.TIME, description="Optimisation strategy"),
    transport_modes: List[str] | None = Query(
        None,
        description="Optional list of desired transport modes (walk, bike, electric_cart)",
    ),
    service: RoutingService = Depends(deps.get_routing_service),
) -> RoutePlanResponse:
    try:
        plan = await service.compute_route(
            region_id=region_id,
            start_node_id=start_node_id,
            end_node_id=end_node_id,
            strategy=strategy,
            transport_modes=transport_modes,
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NodeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RouteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc)
    return RoutePlanResponse(
        region_id=plan.region_id,
        strategy=plan.strategy,
        total_distance=plan.total_distance,
        total_time=plan.total_time,
    nodes=[RouteNode.model_validate(node) for node in plan.nodes],
    segments=[RouteSegment.model_validate(segment) for segment in plan.segments],
        generated_at=generated_at,
        allowed_transport_modes=list(plan.allowed_modes),
    )
