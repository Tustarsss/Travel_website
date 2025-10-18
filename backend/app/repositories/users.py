"""Repositories for user persistence (fastapi-users based)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.users import User


class UserRepository:
	"""Data access layer for user entities."""

	def __init__(self, session: AsyncSession):
		self.session = session

	async def create(self, user: User) -> User:
		self.session.add(user)
		await self.session.commit()
		await self.session.refresh(user)
		return user

	async def get_by_id(self, user_id: UUID) -> Optional[User]:
		result = await self.session.execute(select(User).where(User.id == user_id))
		return result.scalar_one_or_none()

	async def get_by_username(self, username: str) -> Optional[User]:
		result = await self.session.execute(select(User).where(User.username == username))
		return result.scalar_one_or_none()

	async def update_last_login(self, user_id: UUID, timestamp: datetime) -> None:
		await self.session.execute(
			update(User)
			.where(User.id == user_id)
			.values(last_login_at=timestamp)
		)
		await self.session.commit()


__all__ = ["UserRepository"]
