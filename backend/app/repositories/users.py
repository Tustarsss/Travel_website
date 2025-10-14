"""Repositories for user and session persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.users import User
from app.models.sessions import UserSession


class UserRepository:
	"""Data access layer for user entities."""

	def __init__(self, session: AsyncSession):
		self.session = session

	async def create(self, user: User) -> User:
		self.session.add(user)
		await self.session.commit()
		await self.session.refresh(user)
		return user

	async def get_by_id(self, user_id: int) -> Optional[User]:
		result = await self.session.execute(select(User).where(User.id == user_id))
		return result.scalar_one_or_none()

	async def get_by_username(self, username: str) -> Optional[User]:
		result = await self.session.execute(select(User).where(User.username == username))
		return result.scalar_one_or_none()

	async def update_last_login(self, user_id: int, timestamp: datetime) -> None:
		await self.session.execute(
			update(User)
			.where(User.id == user_id)
			.values(last_login_at=timestamp)
		)
		await self.session.commit()


class UserSessionRepository:
	"""Persistence helper for refresh token sessions."""

	def __init__(self, session: AsyncSession):
		self.session = session

	async def create(self, session_model: UserSession) -> UserSession:
		self.session.add(session_model)
		await self.session.commit()
		await self.session.refresh(session_model)
		return session_model

	async def save(self, session_model: UserSession) -> UserSession:
		self.session.add(session_model)
		await self.session.commit()
		await self.session.refresh(session_model)
		return session_model

	async def get_active_by_token_hash(self, token_hash: str) -> Optional[UserSession]:
		result = await self.session.execute(
			select(UserSession)
			.where(UserSession.refresh_token_hash == token_hash)
			.where(UserSession.is_active.is_(True))
		)
		return result.scalar_one_or_none()

	async def deactivate(self, session_model: UserSession) -> None:
		session_model.is_active = False
		await self.session.commit()

	async def deactivate_by_user(self, user_id: int) -> None:
		await self.session.execute(
			update(UserSession)
			.where(UserSession.user_id == user_id)
			.values(is_active=False)
		)
		await self.session.commit()

	async def delete_expired(self, reference: datetime) -> int:
		result = await self.session.execute(
			select(UserSession).where(UserSession.expires_at < reference)
		)
		sessions = result.scalars().all()
		for sess in sessions:
			await self.session.delete(sess)
		await self.session.commit()
		return len(sessions)
