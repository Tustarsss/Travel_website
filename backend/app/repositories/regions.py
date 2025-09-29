"""Repository helpers for region entities."""

from __future__ import annotations

from typing import Iterable

from sqlalchemy import func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.locations import Region, RegionType


class RegionRepository:
    """Data access helpers for :class:`~app.models.locations.Region`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_regions(
        self,
        *,
        search: str | None = None,
        region_type: RegionType | None = None,
        limit: int | None = None,
    ) -> list[Region]:
        """Return regions optionally filtered by search term and type."""

        statement = select(Region)

        if region_type is not None:
            statement = statement.where(Region.type == region_type)

        if search:
            pattern = f"%{search.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(Region.name).like(pattern),
                    func.lower(func.coalesce(Region.city, "")).like(pattern),
                    func.lower(func.coalesce(Region.description, "")).like(pattern),
                )
            )

        statement = statement.order_by(Region.popularity.desc(), Region.rating.desc(), Region.name.asc())

        if limit is not None and limit > 0:
            statement = statement.limit(limit)

        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_region(self, region_id: int) -> Region | None:
        statement = select(Region).where(Region.id == region_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_regions(self, *, region_type: RegionType | None = None) -> list[Region]:
        """Return all regions, optionally filtered by type."""

        return await self.fetch_regions(search=None, region_type=region_type)

    async def search_regions(self, keyword: str, *, limit: int = 10) -> list[Region]:
        """Search regions by keyword with optional limit."""

        if not keyword or not keyword.strip() or limit <= 0:
            return []

        return await self.fetch_regions(search=keyword.strip(), region_type=None, limit=limit)

    async def upsert_regions(self, regions: Iterable[Region]) -> None:
        """Persist regions, inserting new records and updating existing ones."""

        for region in regions:
            self._session.add(region)
        await self._session.commit()

    async def delete_all(self) -> None:
        """Remove all region records."""

        await self._session.execute(text("DELETE FROM regions"))
        await self._session.commit()
