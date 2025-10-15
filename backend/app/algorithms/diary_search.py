"""Full-text search utilities for diary content using SQLite FTS5."""

import re
from typing import List, Optional, Tuple

from sqlalchemy import text  # type: ignore[import-untyped]
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.diaries import Diary


class DiarySearchService:
    """Full-text search service for diaries using SQLite FTS5."""

    FTS_TABLE_NAME = "diaries_fts"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def initialize_fts_table(self) -> None:
        """
        Initialize FTS5 virtual table for diary search.
        This should be called during database setup.
        """
        # Recreate triggers to ensure latest definitions
        drop_triggers = [
            "DROP TRIGGER IF EXISTS diaries_fts_insert",
            "DROP TRIGGER IF EXISTS diaries_fts_update",
            "DROP TRIGGER IF EXISTS diaries_fts_delete",
        ]

        # Create FTS5 virtual table
        create_table_sql = f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS {self.FTS_TABLE_NAME} USING fts5(
            diary_id UNINDEXED,
            title,
            content,
            tags,
            tokenize = 'porter unicode61'
        );
        """

        # Create triggers to keep FTS table in sync
        triggers = [
            f"""
            CREATE TRIGGER IF NOT EXISTS diaries_fts_insert AFTER INSERT ON diaries
            BEGIN
                INSERT INTO {self.FTS_TABLE_NAME}(diary_id, title, content, tags)
                VALUES (new.id, new.title, new.content, json(new.tags));
            END;
            """,
            f"""
            CREATE TRIGGER IF NOT EXISTS diaries_fts_update AFTER UPDATE ON diaries
            BEGIN
                UPDATE {self.FTS_TABLE_NAME} SET
                    title = new.title,
                    content = new.content,
                    tags = json(new.tags)
                WHERE diary_id = new.id;
            END;
            """,
            f"""
            CREATE TRIGGER IF NOT EXISTS diaries_fts_delete AFTER DELETE ON diaries
            BEGIN
                DELETE FROM {self.FTS_TABLE_NAME} WHERE diary_id = old.id;
            END;
            """,
        ]

        async with self.session.begin():
            for drop_sql in drop_triggers:
                await self.session.execute(text(drop_sql))
            await self.session.execute(text(create_table_sql))
            for trigger_sql in triggers:
                await self.session.execute(text(trigger_sql))

    async def search_diaries(
        self,
        query: str,
        limit: int = 20,
        region_id: Optional[int] = None,
    ) -> List[Tuple[Diary, float, List[str]]]:
        """
        Perform full-text search on diaries.

        Args:
            query: Search query string
            limit: Maximum number of results
            region_id: Optional region filter

        Returns:
            List of (diary, relevance_score, matched_fields) tuples
        """
        if not query.strip():
            return []

        # Process query for better search results
        processed_query = self._process_query(query)

        # Build search query with relevance scoring
        base_sql = f"""
        SELECT
            d.*,
            bm25({self.FTS_TABLE_NAME}) as relevance_score,
            CASE
                WHEN fts.title MATCH :query THEN 'title'
                ELSE NULL
            END as title_match,
            CASE
                WHEN fts.content MATCH :query THEN 'content'
                ELSE NULL
            END as content_match,
            CASE
                WHEN fts.tags MATCH :query THEN 'tags'
                ELSE NULL
            END as tags_match
        FROM {self.FTS_TABLE_NAME} fts
        JOIN diaries d ON d.id = fts.diary_id
        WHERE fts.{self.FTS_TABLE_NAME} MATCH :query
        AND d.status = 'published'
        """

        params = {'query': processed_query}

        # Add region filter if specified
        if region_id:
            base_sql += " AND d.region_id = :region_id"
            params['region_id'] = region_id

        # Order by relevance and limit results
        base_sql += " ORDER BY relevance_score LIMIT :limit"
        params['limit'] = limit

        result = await self.session.execute(text(base_sql), params)

        diaries_with_scores = []
        for row in result:
            diary_data = dict(row)
            relevance_score = diary_data.pop('relevance_score', 0.0)

            # Extract matched fields
            matched_fields = []
            if diary_data.get('title_match'):
                matched_fields.append('title')
            if diary_data.get('content_match'):
                matched_fields.append('content')
            if diary_data.get('tags_match'):
                matched_fields.append('tags')

            # Remove match indicator columns
            for key in ['title_match', 'content_match', 'tags_match']:
                diary_data.pop(key, None)

            # Convert to Diary object (simplified - in practice you'd use proper ORM loading)
            diary = Diary(**{k: v for k, v in diary_data.items() if k in Diary.__annotations__})

            # Normalize relevance score (bm25 can be negative, we want 0-1 range)
            normalized_score = max(0.0, 1.0 - (relevance_score / 100.0))

            diaries_with_scores.append((diary, normalized_score, matched_fields))

        return diaries_with_scores

    async def rebuild_fts_index(self) -> None:
        """
        Rebuild the FTS index from scratch.
        Useful for maintenance or after bulk data changes.
        """
        # Clear existing FTS data
        await self.session.execute(text(f"DELETE FROM {self.FTS_TABLE_NAME}"))

        # Re-populate from diaries table
        insert_sql = f"""
    INSERT INTO {self.FTS_TABLE_NAME}(diary_id, title, content, tags)
    SELECT id, title, content, json(tags)
    FROM diaries
    WHERE status = 'published'
        """

        await self.session.execute(text(insert_sql))
        await self.session.commit()

    def _process_query(self, query: str) -> str:
        """
        Process search query for better results.

        - Tokenize Chinese text (basic implementation)
        - Support boolean operators
        - Handle phrases
        """
        # Remove extra whitespace
        query = query.strip()

        # For Chinese text, split into individual characters if no spaces
        if not any(c.isspace() for c in query):
            # Simple Chinese character splitting (can be improved with jieba)
            if any('\u4e00' <= c <= '\u9fff' for c in query):
                # Split Chinese characters and keep English words together
                tokens = []
                current_word = ""
                for char in query:
                    if '\u4e00' <= char <= '\u9fff':
                        if current_word:
                            tokens.append(f'"{current_word}"')
                            current_word = ""
                        tokens.append(char)
                    elif char.isalnum():
                        current_word += char
                    else:
                        if current_word:
                            tokens.append(f'"{current_word}"')
                            current_word = ""
                if current_word:
                    tokens.append(f'"{current_word}"')

                return ' OR '.join(tokens)

        # For English/other languages, use phrase search
        words = query.split()
        if len(words) == 1:
            return f'"{words[0]}"'
        else:
            # Search for the full phrase AND individual words
            return f'"{query}" OR {" OR ".join(f'"{word}"' for word in words)}'

    async def get_search_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """
        Get search suggestions based on prefix matching.

        Args:
            prefix: Prefix to match
            limit: Maximum suggestions to return

        Returns:
            List of suggested search terms
        """
        if not prefix.strip():
            return []

        # Query for terms starting with the prefix
        sql = f"""
        SELECT term FROM {self.FTS_TABLE_NAME}_vocab
        WHERE term LIKE ?
        ORDER BY term
        LIMIT ?
        """

        result = await self.session.execute(text(sql), (f"{prefix}%", limit))

        return [row[0] for row in result]


# Singleton instance factory
def get_diary_search_service(session: AsyncSession) -> DiarySearchService:
    """Get diary search service instance."""
    return DiarySearchService(session)