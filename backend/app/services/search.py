"""Search-focused service utilities for keyword lookups."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.graph import GraphNode
from app.models.locations import Building, Facility, Region, RegionType
from app.repositories import GraphRepository, RegionRepository


@dataclass(slots=True)
class RegionSearchHit:
    """Lightweight region representation for keyword search results."""

    id: int
    name: str
    type: RegionType | None
    city: str | None
    description: str | None
    latitude: float | None
    longitude: float | None
    keywords: list[str]


@dataclass(slots=True)
class RegionNodeSearchHit:
    """Graph node search hit enriched with contextual metadata."""

    id: int
    region_id: int
    name: str
    latitude: float | None
    longitude: float | None
    code: str | None
    description: str | None


class SearchService:
    """High level search operations for regions and graph nodes."""

    def __init__(self, region_repository: RegionRepository, graph_repository: GraphRepository) -> None:
        self._region_repository = region_repository
        self._graph_repository = graph_repository

    async def search_regions(self, keyword: str, *, limit: int = 10) -> list[RegionSearchHit]:
        regions = await self._region_repository.search_regions(keyword, limit=limit)
        return [self._to_region_hit(region) for region in regions]

    async def get_region(self, region_id: int) -> RegionSearchHit | None:
        region = await self._region_repository.get_region(region_id)
        if region is None:
            return None
        return self._to_region_hit(region)

    async def search_region_nodes(
        self, region_id: int, keyword: str, *, limit: int = 15
    ) -> list[RegionNodeSearchHit]:
        results = await self._graph_repository.search_nodes(region_id, keyword, limit=limit)
        hits: list[RegionNodeSearchHit] = []
        for node, building, facility in results:
            if node.id is None:
                continue
            hits.append(self._to_node_hit(node, building, facility))
        return hits

    async def get_region_node(
        self, region_id: int, node_id: int
    ) -> RegionNodeSearchHit | None:
        node, building, facility = await self._graph_repository.get_node_with_context(node_id)
        if node is None or node.region_id != region_id:
            return None
        return self._to_node_hit(node, building, facility)

    def _to_region_hit(self, region: Region) -> RegionSearchHit:
        return RegionSearchHit(
            id=region.id,
            name=region.name,
            type=region.type,
            city=region.city,
            description=region.description,
            latitude=region.latitude,
            longitude=region.longitude,
            keywords=self._generate_region_keywords(region),
        )

    def _generate_region_keywords(self, region: Region) -> list[str]:
        tokens: list[str] = []
        tokens.extend(self._tokenise(region.name))
        if region.city:
            tokens.extend(self._tokenise(region.city))
        if region.description:
            tokens.extend(self._tokenise(region.description))
        return sorted(set(tokens))

    def _tokenise(self, text: str) -> list[str]:
        return [chunk for chunk in text.replace("-", " ").replace("/", " ").split() if chunk]

    def _to_node_hit(
        self,
        node: GraphNode,
        building: Building | None,
        facility: Facility | None,
    ) -> RegionNodeSearchHit:
        name = node.name or facility.name if facility else None
        if not name and building:
            name = building.name
        if not name:
            name = f"节点 {node.id}"

        description_parts: list[str] = []
        if facility and facility.name:
            description_parts.append(f"设施：{facility.name}")
        if building and building.name:
            description_parts.append(f"建筑：{building.name}")

        description = "；".join(description_parts) if description_parts else None

        code = None
        if building and building.id:
            code = f"B-{building.id}"
        elif facility and facility.id:
            code = f"F-{facility.id}"

        return RegionNodeSearchHit(
            id=node.id,
            region_id=node.region_id,
            name=name,
            latitude=node.latitude,
            longitude=node.longitude,
            code=code,
            description=description,
        )

__all__ = ["SearchService", "RegionSearchHit", "RegionNodeSearchHit"]
