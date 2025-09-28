"""Repository helpers for facility entities."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.graph import GraphNode
from app.models.locations import Facility
from app.models.enums import FacilityCategory


class FacilityRepository:
    """Data access helper for facilities and their graph associations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_facilities_with_nodes(
        self,
        region_id: int,
        *,
        categories: Sequence[FacilityCategory] | None = None,
    ) -> list[tuple[Facility, GraphNode]]:
        """Return facilities within a region joined with their graph nodes."""

        statement = (
            select(Facility, GraphNode)
            .join(GraphNode, GraphNode.facility_id == Facility.id)
            .where(Facility.region_id == region_id)
        )

        if categories:
            statement = statement.where(Facility.category.in_(categories))

        result = await self._session.execute(statement)
        return [(facility, node) for facility, node in result.all()]

    async def list_facilities(
        self,
        region_id: int,
        *,
        categories: Sequence[FacilityCategory] | None = None,
    ) -> list[Facility]:
        """Return facilities for a region without graph information."""

        statement = select(Facility).where(Facility.region_id == region_id)
        if categories:
            statement = statement.where(Facility.category.in_(categories))
        result = await self._session.execute(statement)
        return list(result.scalars().all())
