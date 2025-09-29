"""Keyword search and region discovery endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api import deps
from app.schemas import (
	RegionNodeSearchResponse,
	RegionNodeSummary,
	RegionSearchResponse,
	RegionSearchResult,
)
from app.services.search import SearchService

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("/search", response_model=RegionSearchResponse)
async def search_regions(
	*,
	q: str = Query(..., min_length=1, description="关键词"),
	limit: int = Query(10, ge=1, le=50, description="返回结果数量上限"),
	service: SearchService = Depends(deps.get_search_service),
) -> RegionSearchResponse:
	"""Search regions by keyword."""

	hits = await service.search_regions(q, limit=limit)
	items = [RegionSearchResult.model_validate(hit) for hit in hits]
	return RegionSearchResponse(items=items)


@router.get("/{region_id}", response_model=RegionSearchResult)
async def get_region_detail(
	region_id: int,
	service: SearchService = Depends(deps.get_search_service),
) -> RegionSearchResult:
	"""Retrieve detailed metadata for a region."""

	hit = await service.get_region(region_id)
	if hit is None:
		raise HTTPException(status_code=404, detail="Region not found")
	return RegionSearchResult.model_validate(hit)


@router.get("/{region_id}/nodes/search", response_model=RegionNodeSearchResponse)
async def search_region_nodes(
	*,
	region_id: int,
	q: str = Query(..., min_length=1, description="节点关键词"),
	limit: int = Query(10, ge=1, le=50, description="返回结果数量上限"),
	service: SearchService = Depends(deps.get_search_service),
) -> RegionNodeSearchResponse:
	"""Search nodes within a region by keyword."""

	hits = await service.search_region_nodes(region_id, q, limit=limit)
	items = [RegionNodeSummary.model_validate(hit) for hit in hits]
	return RegionNodeSearchResponse(items=items)


@router.get("/{region_id}/nodes/{node_id}", response_model=RegionNodeSummary)
async def get_region_node_detail(
	*,
	region_id: int,
	node_id: int,
	service: SearchService = Depends(deps.get_search_service),
) -> RegionNodeSummary:
	"""Retrieve detailed information for a specific node within a region."""

	hit = await service.get_region_node(region_id, node_id)
	if hit is None:
		raise HTTPException(status_code=404, detail="Region node not found")
	return RegionNodeSummary.model_validate(hit)
