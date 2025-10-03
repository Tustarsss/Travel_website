"""Initialize FTS5 full-text search for diaries."""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.diary_search import get_diary_search_service
from app.core.db import get_session_maker


async def init_fts_tables():
    """Initialize FTS5 tables and triggers for diary search."""
    maker = get_session_maker()
    async with maker() as session:
        search_service = get_diary_search_service(session)
        await search_service.initialize_fts_table()
        print("FTS5 tables initialized successfully")


if __name__ == "__main__":
    asyncio.run(init_fts_tables())