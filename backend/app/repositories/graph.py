"""Repository helpers for graph nodes and edges."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.graph import GraphEdge, GraphNode


class GraphRepository:
    """Data access layer for routing graph entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_node(self, node_id: int) -> GraphNode | None:
        statement = select(GraphNode).where(GraphNode.id == node_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

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

    async def upsert_nodes(self, nodes: Iterable[GraphNode]) -> None:
        for node in nodes:
            self._session.add(node)
        await self._session.commit()

    async def upsert_edges(self, edges: Iterable[GraphEdge]) -> None:
        for edge in edges:
            self._session.add(edge)
        await self._session.commit()
