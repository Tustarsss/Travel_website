"""Create optimized database indexes for diary operations."""

import asyncio
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session_maker


async def create_optimized_indexes():
    """Create performance-optimized indexes for diary queries."""

    indexes = [
        # Core query indexes (from design doc)
        """
        CREATE INDEX IF NOT EXISTS idx_diaries_region_status
        ON diaries(region_id, status);
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_diaries_popularity
        ON diaries(popularity DESC);
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_diaries_rating
        ON diaries(rating DESC);
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_diaries_created_at
        ON diaries(created_at DESC);
        """,

        # Composite indexes for recommendation algorithm
        """
        CREATE INDEX IF NOT EXISTS idx_diaries_composite
        ON diaries(status, region_id, popularity DESC, rating DESC);
        """,

        # Diary ratings indexes
        """
        CREATE INDEX IF NOT EXISTS idx_diary_ratings_diary_id
        ON diary_ratings(diary_id);
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_diary_ratings_user_id
        ON diary_ratings(user_id);
        """,

        # Diary views indexes
        """
        CREATE INDEX IF NOT EXISTS idx_diary_views_diary_id
        ON diary_views(diary_id);
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_diary_views_user_id
        ON diary_views(user_id);
        """,

        # Diary animations indexes
        """
        CREATE INDEX IF NOT EXISTS idx_diary_animations_diary_id
        ON diary_animations(diary_id);
        """,

        # Users indexes
        """
        CREATE INDEX IF NOT EXISTS idx_users_username
        ON users(username);
        """,

        # Regions indexes
        """
        CREATE INDEX IF NOT EXISTS idx_regions_type
        ON regions(type);
        """,
    ]

    maker = get_session_maker()
    async with maker() as session:
        for index_sql in indexes:
            try:
                await session.execute(text(index_sql))
                print(f"Created index: {index_sql.strip().split('ON')[1].split('(')[0].strip()}")
            except Exception as e:
                print(f"Failed to create index: {e}")

        await session.commit()
        print("All indexes created successfully")


async def analyze_query_performance():
    """Analyze query performance and suggest optimizations."""

    analysis_queries = [
        "ANALYZE;",  # Update query statistics
        "EXPLAIN QUERY PLAN SELECT * FROM diaries WHERE status = 'published' ORDER BY popularity DESC LIMIT 10;",
        "EXPLAIN QUERY PLAN SELECT * FROM diaries WHERE region_id = 1 AND status = 'published';",
        "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM diary_ratings WHERE diary_id = 1;",
    ]

    maker = get_session_maker()
    async with maker() as session:
        print("\n=== Query Performance Analysis ===")

        for query in analysis_queries:
            print(f"\nQuery: {query}")
            try:
                result = await session.execute(text(query))
                rows = result.fetchall()
                for row in rows:
                    print(f"  {row}")
            except Exception as e:
                print(f"  Error: {e}")


if __name__ == "__main__":
    asyncio.run(create_optimized_indexes())
    asyncio.run(analyze_query_performance())