"""Service layer for diary business logic."""

from datetime import datetime
from typing import List, Optional

from app.algorithms.diary_ranking import ranking_algorithm
from app.algorithms.diary_compression import compression_service
from app.models.diaries import Diary, DiaryAnimation
from app.models.enums import DiaryStatus
from app.repositories.diaries import DiaryRepository
from app.schemas.diary import (
    DiaryCreateRequest,
    DiaryUpdateRequest,
    DiaryListParams,
)
from app.services.cache_service import diary_cache_service


class DiaryService:
    """Business logic for diary operations."""

    def __init__(self, repo: DiaryRepository):
        self.repo = repo

    async def create_diary(
        self,
        user_id: int,
        request: DiaryCreateRequest,
    ) -> tuple[Diary, dict]:
        """
        Create a new diary with automatic compression.
        
        Returns:
            Tuple of (diary, compression_stats)
        """
        # Compress content
        compressed_data, is_compressed, ratio = compression_service.compress_content(
            request.content
        )
        
        # Create diary object
        diary = Diary(
            user_id=user_id,
            region_id=request.region_id,
            title=request.title,
            summary=request.summary,
            content=request.content,  # Keep original for immediate use
            compressed_content=compressed_data if is_compressed else None,
            is_compressed=is_compressed,
            media_urls=request.media_urls,
            media_types=request.media_types,
            tags=request.tags,
            status=request.status,
        )
        
        # Save to database
        created = await self.repo.create(diary)
        
        # Prepare compression stats
        compression_stats = {
            'compressed': is_compressed,
            'ratio': ratio if is_compressed else None,
        }
        
        return created, compression_stats

    async def get_diary(
        self,
        diary_id: int,
        decompress: bool = True,
    ) -> Optional[Diary]:
        """
        Get diary by ID with automatic decompression.
        
        Args:
            diary_id: ID of the diary
            decompress: If True, decompress content if needed
        """
        diary = await self.repo.get_by_id(diary_id)
        
        if diary and decompress and diary.is_compressed and diary.compressed_content:
            # Decompress content for reading
            try:
                diary.content = compression_service.decompress_content(
                    diary.compressed_content,
                    diary.is_compressed
                )
            except ValueError as e:
                print(f"Decompression error for diary {diary_id}: {e}")
                # Keep original content if decompression fails
        
        return diary

    async def update_diary(
        self,
        diary_id: int,
        user_id: int,
        request: DiaryUpdateRequest,
    ) -> Optional[Diary]:
        """Update an existing diary."""
        diary = await self.repo.get_by_id(diary_id, load_relationships=False)
        
        if not diary:
            return None
        
        # Check ownership
        if diary.user_id != user_id:
            raise PermissionError("You can only edit your own diaries")
        
        # Update fields
        if request.title is not None:
            diary.title = request.title
        if request.summary is not None:
            diary.summary = request.summary
        if request.content is not None:
            # Re-compress if content changed
            compressed_data, is_compressed, _ = compression_service.compress_content(
                request.content
            )
            diary.content = request.content
            diary.compressed_content = compressed_data if is_compressed else None
            diary.is_compressed = is_compressed
        if request.region_id is not None:
            diary.region_id = request.region_id
        if request.tags is not None:
            diary.tags = request.tags
        if request.media_urls is not None:
            diary.media_urls = request.media_urls
        if request.media_types is not None:
            diary.media_types = request.media_types
        if request.status is not None:
            diary.status = request.status
        
        diary.updated_at = datetime.utcnow()
        
        return await self.repo.update(diary)

    async def delete_diary(
        self,
        diary_id: int,
        user_id: int,
    ) -> bool:
        """Delete a diary (requires ownership)."""
        diary = await self.repo.get_by_id(diary_id, load_relationships=False)
        
        if not diary:
            return False
        
        # Check ownership
        if diary.user_id != user_id:
            raise PermissionError("You can only delete your own diaries")
        
        await self.repo.delete(diary)
        return True

    async def list_diaries(
        self,
        params: DiaryListParams,
    ) -> tuple[List[Diary], int]:
        """
        List diaries with filtering and pagination.
        
        Returns:
            Tuple of (diaries, total_count)
        """
        return await self.repo.list_diaries(
            page=params.page,
            page_size=params.page_size,
            region_id=params.region_id,
            author_id=params.author_id,
            status=params.status,
            tags=params.interests if params.interests else None,
            search_query=params.q,
        )

    async def recommend_diaries(
        self,
        limit: int = 10,
        sort_by: str = 'hybrid',
        interests: Optional[List[str]] = None,
        region_id: Optional[int] = None,
    ) -> List[tuple[Diary, float]]:
        """
        Get personalized diary recommendations using Top-K algorithm.

        Args:
            limit: Number of recommendations to return
            sort_by: Sorting strategy ('hybrid', 'popularity', 'rating', 'latest')
            interests: User interest tags for personalized recommendations
            region_id: Filter by specific region

        Returns:
            List of (diary, score) tuples sorted by score descending
        """
        # Get candidate diaries (published status, optionally filtered by region)
        candidates = await self.repo.list_diaries(
            page=1,
            page_size=1000,  # Large enough to get good candidates
            region_id=region_id,
            status=DiaryStatus.PUBLISHED,
        )

        if not candidates[0]:  # Empty result
            return []

        diaries = candidates[0]

        # Select scoring function based on sort_by
        if sort_by == 'popularity':
            score_func = lambda d: ranking_algorithm.popularity_score(d)
        elif sort_by == 'rating':
            score_func = lambda d: ranking_algorithm.rating_score(d)
        elif sort_by == 'latest':
            score_func = lambda d: ranking_algorithm.recency_score(d)
        else:  # hybrid (default)
            score_func = lambda d: ranking_algorithm.hybrid_score(d, interests)

        # Get top K results
        top_diaries = ranking_algorithm.top_k_by_score(diaries, limit, score_func)

        # Return with scores
        results = []
        for diary in top_diaries:
            score = score_func(diary)
            results.append((diary, score))

        return results

    async def record_view(
        self,
        diary_id: int,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Record a diary view and update popularity."""
        diary = await self.repo.get_by_id(diary_id, load_relationships=False)
        
        if not diary:
            return False
        
        await self.repo.record_view(
            diary_id=diary_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return True

    async def rate_diary(
        self,
        diary_id: int,
        user_id: int,
        score: int,
        comment: Optional[str] = None,
    ):
        """Add or update a user's rating for a diary."""
        # Verify diary exists
        diary = await self.repo.get_by_id(diary_id, load_relationships=False)
        if not diary:
            raise ValueError("Diary not found")
        
        # Add rating
        rating = await self.repo.add_rating(
            diary_id=diary_id,
            user_id=user_id,
            score=score,
            comment=comment,
        )
        
        return rating

    async def get_user_diaries(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        status: Optional[DiaryStatus] = None,
    ) -> tuple[List[Diary], int]:
        """Get all diaries by a user."""
        return await self.repo.list_diaries(
            page=page,
            page_size=page_size,
            author_id=user_id,
            status=status,
        )

    # === Animation Operations ===

    async def create_animation_task(
        self,
        diary_id: int,
        generation_params: dict,
    ) -> DiaryAnimation:
        """
        Create an animation generation task.
        
        Uses AIGC service to generate travel animations.
        """
        from app.services.aigc_service import get_aigc_service
        
        aigc_service = get_aigc_service(self.repo)
        return await aigc_service.generate_animation(diary_id, generation_params)

    async def update_animation_status(
        self,
        animation_id: int,
        status: str,
        progress: int = 0,
        video_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[DiaryAnimation]:
        """Update animation generation status."""
        return await self.repo.update_animation(
            animation_id,
            status=status,
            progress=progress,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            error_message=error_message,
        )

    async def get_diary_animations(
        self,
        diary_id: int,
    ) -> List[DiaryAnimation]:
        """Get all animations for a diary."""
        return await self.repo.get_animations(diary_id)

    async def search_diaries(
        self,
        query: str,
        limit: int = 20,
        region_id: Optional[int] = None,
    ) -> List[tuple[Diary, float, List[str]]]:
        """
        Perform full-text search on diaries.
        
        Returns:
            List of (diary, relevance_score, matched_fields) tuples
        """
        from app.algorithms.diary_search import get_diary_search_service
        
        search_service = get_diary_search_service(self.repo.session)
        return await search_service.search_diaries(query, limit, region_id)
