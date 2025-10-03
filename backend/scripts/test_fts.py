"""Test script for diary search functionality."""

import asyncio
from app.core.db import get_session_maker
from app.algorithms.diary_search import get_diary_search_service


async def test_fts_search():
    """Test FTS search functionality."""
    maker = get_session_maker()
    async with maker() as session:
        search_service = get_diary_search_service(session)

        # Initialize FTS table
        print("Initializing FTS table...")
        await search_service.initialize_fts_table()

        # Test search (this will be empty since we have no data)
        print("Testing search...")
        results = await search_service.search_diaries("test query", limit=5)
        print(f"Search results: {len(results)} found")

        print("FTS search test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_fts_search())