"""Service layer for diary business logic."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urljoin

from app.algorithms.diary_ranking import ranking_algorithm
from app.algorithms.diary_compression import compression_service
from app.algorithms.media_compression import media_compression_service
from app.core.config import settings
from app.models.diaries import Diary, DiaryAnimation, DiaryMedia
from app.models.enums import DiaryMediaType, DiaryStatus
from app.repositories.diaries import DiaryRepository
from app.schemas.diary import (
    DiaryCreateRequest,
    DiaryListParams,
    DiaryUpdateRequest,
)
from app.services.cache_service import diary_cache_service

if TYPE_CHECKING:
    from app.models.locations import Region


@dataclass
class PendingDiaryMedia:
    """In-memory representation of an uploaded media asset awaiting persistence."""

    placeholder: str
    media_type: DiaryMediaType
    filename: str
    content_type: str
    data: bytes


class DiaryService:
    """Business logic for diary operations."""

    def __init__(self, repo: DiaryRepository):
        self.repo = repo
        self._media_placeholder_pattern = re.compile(r"\{\{media:(?P<key>[a-zA-Z0-9_\-\.]+)\}\}")

    async def create_diary(
        self,
        user_id: int,
        request: DiaryCreateRequest,
        media_uploads: Optional[List[PendingDiaryMedia]] = None,
    ) -> tuple[Diary, dict]:
        """
        Create a new diary with automatic compression.
        
        Returns:
            Tuple of (diary, compression_stats)
        """
        media_uploads = media_uploads or []

        # Create diary with raw content (placeholders will be rendered after media persists)
        diary = Diary(
            user_id=user_id,
            region_id=request.region_id,
            title=request.title,
            content=request.content,
            compressed_content=None,
            is_compressed=False,
            media_urls=[],
            media_types=[],
            tags=request.tags,
            status=request.status,
        )
        
        # Save to database
        created = await self.repo.create(diary)
        
        # Persist media assets
        placeholder_to_media: Dict[str, DiaryMedia] = {}
        ordered_media: List[DiaryMedia] = []
        for upload in media_uploads:
            payload, is_media_compressed, _ = media_compression_service.compress(upload.data)
            if not is_media_compressed:
                payload = upload.data
            media_record = await self.repo.add_media(
                diary_id=created.id,
                placeholder=upload.placeholder,
                filename=upload.filename,
                content_type=upload.content_type,
                media_type=upload.media_type,
                payload=payload,
                is_compressed=is_media_compressed,
                original_size=len(upload.data),
                compressed_size=len(payload),
            )
            placeholder_to_media[upload.placeholder] = media_record
            ordered_media.append(media_record)

        # Render final HTML content with embedded media
        rendered_content = self._render_content_with_media(
            request.content,
            placeholder_to_media,
            created.id,
        )

        compressed_data, is_text_compressed, ratio = compression_service.compress_content(
            rendered_content
        )

        created.content = rendered_content
        created.compressed_content = compressed_data if is_text_compressed else None
        created.is_compressed = is_text_compressed
        created.media_urls = [self._build_media_url(created.id, media.id) for media in ordered_media]
        created.media_types = [media.media_type for media in ordered_media]
        created.updated_at = datetime.utcnow()

        updated = await self.repo.update(created)

        compression_stats = {
            "compressed": is_text_compressed,
            "ratio": ratio if is_text_compressed else None,
        }

        return updated, compression_stats

    def _render_content_with_media(
        self,
        raw_content: str,
        media_lookup: Dict[str, DiaryMedia],
        diary_id: int,
    ) -> str:
        """Convert raw diary text with placeholders into sanitized HTML."""

        parts: List[str] = []
        cursor = 0

        used_placeholders: set[str] = set()

        for match in self._media_placeholder_pattern.finditer(raw_content):
            text_segment = raw_content[cursor:match.start()]
            if text_segment:
                parts.append(self._render_text_segment(text_segment))

            placeholder = match.group("key")
            media = media_lookup.get(placeholder)
            if media:
                used_placeholders.add(placeholder)
                parts.append(self._render_media_element(diary_id, media))
            else:
                escaped_key = html.escape(placeholder)
                parts.append(
                    f'<p class="missing-media" data-placeholder="{escaped_key}">'  # noqa: E501
                    f"[媒体 {escaped_key} 未找到]"
                    "</p>"
                )
            cursor = match.end()

        # Trailing text segment
        tail_segment = raw_content[cursor:]
        if tail_segment:
            parts.append(self._render_text_segment(tail_segment))

        unused_media = [media for key, media in media_lookup.items() if key not in used_placeholders]
        if unused_media:
            if parts and not parts[-1].endswith("</p>"):
                parts.append("<p></p>")
            for media in unused_media:
                parts.append(self._render_media_element(diary_id, media))

        html_content = "".join(parts).strip()
        return html_content or "<p></p>"

    def _render_text_segment(self, segment: str) -> str:
        """Escape user text and convert line breaks into paragraphs."""

        if not segment:
            return ""

        paragraphs = segment.split("\n\n")
        rendered: List[str] = []
        for paragraph in paragraphs:
            stripped = paragraph.strip("\n")
            if not stripped:
                continue
            lines = [html.escape(line) for line in stripped.split("\n")]
            rendered.append("<p>" + "<br />".join(lines) + "</p>")

        return "".join(rendered)

    def _render_media_element(self, diary_id: int, media: DiaryMedia) -> str:
        """Render a media element (image/video) as HTML."""

        media_url = self._build_media_url(diary_id, media.id)
        safe_filename = html.escape(media.filename)

        if media.media_type == DiaryMediaType.IMAGE:
            return (
                '<figure class="diary-media diary-media-image" '
                f'data-media-id="{media.id}">'  # noqa: E501
                f'<img src="{media_url}" alt="{safe_filename}" '
                'loading="lazy" />'
                f'<figcaption>{safe_filename}</figcaption>'
                '</figure>'
            )

        return (
            '<figure class="diary-media diary-media-video" '
            f'data-media-id="{media.id}">'  # noqa: E501
            f'<video controls preload="metadata" src="{media_url}"></video>'
            f'<figcaption>{safe_filename}</figcaption>'
            '</figure>'
        )

    def _build_media_url(self, diary_id: int, media_id: int) -> str:
        """Build the public API URL for a diary media resource."""

        base = settings.public_api_url.rstrip("/") + "/"
        path = f"{settings.api_prefix}{settings.api_v1_prefix}/diaries/{diary_id}/media/{media_id}"
        return urljoin(base, path.lstrip("/"))

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

        if diary and diary.media_items:
            ordered_media = sorted(diary.media_items, key=lambda item: item.id)
            diary.media_urls = [self._build_media_url(diary.id, item.id) for item in ordered_media]
            diary.media_types = [item.media_type for item in ordered_media]

            content_html = diary.content or ""
            if "<figure" not in content_html and "{{media:" not in content_html:
                appended = "".join(
                    self._render_media_element(diary.id, media) for media in ordered_media
                )
                diary.content = (content_html + appended).strip() or content_html
        
        return diary

    async def update_diary(
        self,
        diary_id: int,
        user_id: int,
        request: DiaryUpdateRequest,
    ) -> Optional[Diary]:
        """Update an existing diary."""
        diary = await self.repo.get_by_id(diary_id, load_relationships=True)
        
        if not diary:
            return None
        
        # Check ownership
        if diary.user_id != user_id:
            raise PermissionError("You can only edit your own diaries")
        
        # Update fields
        if request.title is not None:
            diary.title = request.title
        if request.content is not None:
            media_lookup = {media.placeholder: media for media in diary.media_items}
            rendered_content = self._render_content_with_media(
                request.content,
                media_lookup,
                diary.id,
            )
            compressed_data, is_compressed, _ = compression_service.compress_content(
                rendered_content
            )
            diary.content = rendered_content
            diary.compressed_content = compressed_data if is_compressed else None
            diary.is_compressed = is_compressed
        if request.region_id is not None:
            diary.region_id = request.region_id
        if request.tags is not None:
            diary.tags = request.tags
        if request.status is not None:
            diary.status = request.status
        
        diary.updated_at = datetime.utcnow()

        if diary.media_items:
            ordered = sorted(diary.media_items, key=lambda item: item.id)
            diary.media_urls = [self._build_media_url(diary.id, item.id) for item in ordered]
            diary.media_types = [item.media_type for item in ordered]
        
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

    async def get_diary_ratings(
        self,
        diary_id: int,
        *,
        page: int = 1,
        page_size: int = 10,
        current_user_id: Optional[int] = None,
    ) -> dict:
        """Retrieve paginated ratings with aggregate statistics."""
        diary = await self.repo.get_by_id(diary_id, load_relationships=False)
        if not diary:
            raise ValueError("Diary not found")

        ratings, total = await self.repo.list_ratings(
            diary_id,
            page=page,
            page_size=page_size,
        )
        stats = await self.repo.get_rating_statistics(diary_id)

        current_user_rating = None
        if current_user_id:
            current_user_rating = await self.repo.get_rating_by_user(diary_id, current_user_id)

        return {
            "items": ratings,
            "total": total,
            "page": page,
            "page_size": page_size,
            "stats": stats,
            "current_user_rating": current_user_rating,
        }

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

    async def get_diary_media_payload(
        self,
        diary_id: int,
        media_id: int,
    ) -> Optional[tuple[DiaryMedia, bytes]]:
        """Retrieve a media record and its decompressed payload."""

        media = await self.repo.get_media(diary_id, media_id)
        if not media:
            return None

        try:
            payload = media_compression_service.decompress(media.data, media.is_compressed)
        except ValueError as exc:
            # Fallback to stored data if decompression fails
            print(f"Media decompression failed for media {media_id}: {exc}")
            payload = media.data

        return media, payload

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

    async def get_region_map(self, region_ids: List[int]) -> dict[int, "Region"]:
        """Fetch regions keyed by id for response assembly."""
        return await self.repo.get_regions_by_ids(region_ids)
