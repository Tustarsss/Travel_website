"""Redis-based caching service for diary operations."""

import json
import pickle
from typing import Any, Optional

import redis.asyncio as redis

from app.core.config import settings


class DiaryCacheService:
    """Redis caching service for diary-related data."""

    def __init__(self):
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        self.cache_ttl = settings.cache_ttl

    # Cache TTL configurations
    CACHE_TTL = {
        'recommendations': 300,  # 5 minutes
        'hot_diaries': 600,      # 10 minutes
        'search_results': 180,   # 3 minutes
        'diary_detail': 1800,    # 30 minutes
        'user_diaries': 600,     # 10 minutes
    }

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        try:
            ttl = ttl or self.cache_ttl
            await self.redis.setex(key, ttl, json.dumps(value))
        except Exception as e:
            print(f"Cache set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        try:
            await self.redis.delete(key)
        except Exception as e:
            print(f"Cache delete error: {e}")

    async def delete_pattern(self, pattern: str) -> None:
        """Delete keys matching pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            print(f"Cache delete pattern error: {e}")

    # Specific cache methods for diary operations

    def _make_recommendations_key(
        self,
        limit: int,
        sort_by: str,
        interests: Optional[list] = None,
        region_id: Optional[int] = None
    ) -> str:
        """Generate cache key for recommendations."""
        interests_str = ','.join(sorted(interests or []))
        return f"diary:rec:{limit}:{sort_by}:{interests_str}:{region_id or 0}"

    async def get_recommendations(
        self,
        limit: int,
        sort_by: str,
        interests: Optional[list] = None,
        region_id: Optional[int] = None
    ) -> Optional[list]:
        """Get cached recommendations."""
        key = self._make_recommendations_key(limit, sort_by, interests, region_id)
        return await self.get(key)

    async def set_recommendations(
        self,
        data: list,
        limit: int,
        sort_by: str,
        interests: Optional[list] = None,
        region_id: Optional[int] = None,
    ) -> None:
        """Cache recommendations."""
        key = self._make_recommendations_key(limit, sort_by, interests, region_id)
        ttl = self.CACHE_TTL['recommendations']
        await self.set(key, data, ttl)

    def _make_search_key(self, query: str, limit: int, region_id: Optional[int] = None) -> str:
        """Generate cache key for search results."""
        return f"diary:search:{query}:{limit}:{region_id or 0}"

    async def get_search_results(self, query: str, limit: int, region_id: Optional[int] = None) -> Optional[list]:
        """Get cached search results."""
        key = self._make_search_key(query, limit, region_id)
        return await self.get(key)

    async def set_search_results(
        self,
        data: list,
        query: str,
        limit: int,
        region_id: Optional[int] = None,
    ) -> None:
        """Cache search results."""
        key = self._make_search_key(query, limit, region_id)
        ttl = self.CACHE_TTL['search_results']
        await self.set(key, data, ttl)

    def _make_hot_diaries_key(self, limit: int) -> str:
        """Generate cache key for hot diaries."""
        return f"diary:hot:{limit}"

    async def get_hot_diaries(self, limit: int) -> Optional[list]:
        """Get cached hot diaries."""
        key = self._make_hot_diaries_key(limit)
        return await self.get(key)

    async def set_hot_diaries(self, limit: int, data: list) -> None:
        """Cache hot diaries."""
        key = self._make_hot_diaries_key(limit)
        ttl = self.CACHE_TTL['hot_diaries']
        await self.set(key, data, ttl)

    def _make_diary_detail_key(self, diary_id: int) -> str:
        """Generate cache key for diary detail."""
        return f"diary:detail:{diary_id}"

    async def get_diary_detail(self, diary_id: int) -> Optional[dict]:
        """Get cached diary detail."""
        key = self._make_diary_detail_key(diary_id)
        return await self.get(key)

    async def set_diary_detail(self, diary_id: int, data: dict) -> None:
        """Cache diary detail."""
        key = self._make_diary_detail_key(diary_id)
        ttl = self.CACHE_TTL['diary_detail']
        await self.set(key, data, ttl)

    def _make_user_diaries_key(self, user_id: str, page: int, page_size: int, status: Optional[str] = None) -> str:
        """Generate cache key for user diaries."""
        status_str = status or 'all'
        return f"diary:user:{user_id}:{page}:{page_size}:{status_str}"

    async def get_user_diaries(
        self,
    user_id: str,
        page: int,
        page_size: int,
        status: Optional[str] = None
    ) -> Optional[dict]:
        """Get cached user diaries."""
        key = self._make_user_diaries_key(user_id, page, page_size, status)
        return await self.get(key)

    async def set_user_diaries(
        self,
        data: dict,
    user_id: str,
        page: int,
        page_size: int,
        status: Optional[str] = None,
    ) -> None:
        """Cache user diaries."""
        key = self._make_user_diaries_key(user_id, page, page_size, status)
        ttl = self.CACHE_TTL['user_diaries']
        await self.set(key, data, ttl)

    # Cache invalidation methods

    async def invalidate_diary_cache(self, diary_id: int) -> None:
        """Invalidate all cache entries related to a specific diary."""
        patterns = [
            f"diary:detail:{diary_id}",
            "diary:rec:*",  # Invalidate all recommendations
            "diary:hot:*",  # Invalidate hot diaries
            "diary:search:*",  # Invalidate search results
        ]

        for pattern in patterns:
            await self.delete_pattern(pattern)

    async def invalidate_user_cache(self, user_id: int) -> None:
        """Invalidate all cache entries related to a specific user."""
        pattern = f"diary:user:{user_id}:*"
        await self.delete_pattern(pattern)

    async def clear_all_cache(self) -> None:
        """Clear all diary-related cache."""
        await self.delete_pattern("diary:*")


# Global cache service instance
diary_cache_service = DiaryCacheService()