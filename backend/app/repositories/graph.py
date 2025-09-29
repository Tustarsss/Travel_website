"""Repository helpers for graph nodes and edges."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.graph import GraphEdge, GraphNode
from app.models.locations import Building, Facility


class GraphRepository:
    """Data access layer for routing graph entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_node(self, node_id: int) -> GraphNode | None:
        statement = select(GraphNode).where(GraphNode.id == node_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_node_with_context(
        self, node_id: int
    ) -> tuple[GraphNode | None, Building | None, Facility | None]:
        statement = (
            select(GraphNode, Building, Facility)
            .outerjoin(Building, Building.id == GraphNode.building_id)
            .outerjoin(Facility, Facility.id == GraphNode.facility_id)
            .where(GraphNode.id == node_id)
        )
        result = await self._session.execute(statement)
        row = result.first()
        if not row:
            return None, None, None
        node, building, facility = row
        return node, building, facility

    async def get_nodes(self, node_ids: Sequence[int]) -> list[GraphNode]:
        if not node_ids:
            return []
        statement = select(GraphNode).where(GraphNode.id.in_(node_ids))
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_nodes_by_region(self, region_id: int) -> list[GraphNode]:
        statement = select(GraphNode).where(GraphNode.region_id == region_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_edges_by_region(self, region_id: int) -> list[GraphEdge]:
        statement = select(GraphEdge).where(GraphEdge.region_id == region_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def search_nodes(
        self,
        region_id: int,
        keyword: str,
        *,
        limit: int = 15,
    ) -> list[tuple[GraphNode, Building | None, Facility | None]]:
        """Search nodes within a region by keyword, joining building/facility metadata."""

        if limit <= 0 or not keyword or not keyword.strip():
            return []

        pattern = f"%{keyword.strip().lower()}%"

        name_field = func.coalesce(func.lower(GraphNode.name), func.lower(Facility.name), func.lower(Building.name))

        statement = (
            select(GraphNode, Building, Facility)
            .outerjoin(Building, Building.id == GraphNode.building_id)
            .outerjoin(Facility, Facility.id == GraphNode.facility_id)
            .where(GraphNode.region_id == region_id)
            .where(
                or_(
                    func.lower(func.coalesce(GraphNode.name, "")).like(pattern),
                    func.lower(func.coalesce(Building.name, "")).like(pattern),
                    func.lower(func.coalesce(Facility.name, "")).like(pattern),
                )
            )
            .order_by(name_field.asc())
            .limit(limit)
        )

        result = await self._session.execute(statement)
        return [(node, building, facility) for node, building, facility in result.all()]

    async def upsert_nodes(self, nodes: Iterable[GraphNode]) -> None:
        for node in nodes:
            self._session.add(node)
        await self._session.commit()

    async def upsert_edges(self, edges: Iterable[GraphEdge]) -> None:
        for edge in edges:
            self._session.add(edge)
        await self._session.commit()
