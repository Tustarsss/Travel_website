"""Database engine and session management."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from .config import settings


DATABASE_URL = settings.database_url

_ASYNC_ENGINE: AsyncEngine | None = None


def get_async_engine() -> AsyncEngine:
	"""Return a cached async engine instance."""

	global _ASYNC_ENGINE
	if _ASYNC_ENGINE is None:
		_ASYNC_ENGINE = create_async_engine(DATABASE_URL, echo=settings.debug, future=True)
	return _ASYNC_ENGINE


def get_session_maker() -> sessionmaker[AsyncSession]:
	"""Create an async sessionmaker bound to the engine."""

	return sessionmaker(get_async_engine(), class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def lifespan_session() -> AsyncGenerator[AsyncSession, None]:
	"""Provide an async session context."""

	async_session = get_session_maker()
	async with async_session() as session:
		yield session


async def init_db_async() -> None:
	"""Ensure database tables exist using the async engine."""

	async with get_async_engine().begin() as conn:
		await conn.run_sync(SQLModel.metadata.create_all)

	# Initialize FTS5 tables after main tables are created
	from app.algorithms.diary_search import get_diary_search_service
	from app.core.db import get_session_maker

	maker = get_session_maker()
	async with maker() as session:
		search_service = get_diary_search_service(session)
		await search_service.initialize_fts_table()


def init_db() -> None:
	"""Create database tables synchronously (for scripts/CLI)."""

	asyncio.run(init_db_async())
