"""API endpoints for diary management."""

import html
import json
import re
import unicodedata
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.responses import StreamingResponse

from app.api import deps
from app.core.config import settings
from app.models.enums import DiaryMediaType, DiaryStatus
from app.models.users import User
from app.repositories.diaries import DiaryRepository
from app.services.diary import DiaryService, PendingDiaryMedia
from app.algorithms.diary_compression import compression_service
from app.schemas.diary import (
    DiaryCreateRequest,
    DiaryMediaItem,
    DiaryMediaPlaceholder,
    DiaryUpdateRequest,
    DiaryDetail,
    DiaryListItem,
    DiaryCreateResponse,
    DiaryRatingRequest,
    DiaryRatingResponse,
    DiaryRatingItem,
    DiaryRatingListResponse,
    DiaryViewRequest,
    DiaryRecommendationItem,
    DiaryRecommendationResponse,
    AnimationGenerateRequest,
    DiaryAnimationResponse,
    UserSummary,
    RegionSummary,
    DiarySearchResult,
    DiarySearchResponse,
)

router = APIRouter(prefix="/diaries", tags=["diaries"])


def _get_diary_service(session: AsyncSession = Depends(deps.get_db_session)) -> DiaryService:
    """Get diary service instance."""
    repo = DiaryRepository(session)
    return DiaryService(repo)


def _build_content_disposition(filename: Optional[str], disposition: str = "inline") -> str:
    """Construct a RFC 5987 compliant Content-Disposition value.

    Provides an ASCII fallback plus UTF-8 encoded filename* so that browsers can
    correctly display non-ASCII characters (e.g., Chinese filenames) without
    triggering Latin-1 encoding errors inside Starlette.
    """

    original = (filename or "").strip() or "media"

    normalized = unicodedata.normalize("NFKD", original)
    ascii_fallback = normalized.encode("ascii", "ignore").decode("ascii").strip()
    ascii_fallback = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_fallback) or "media"

    quoted = quote(original, safe="")
    return f'{disposition}; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quoted}'


def _select_cover_image(diary) -> Optional[str]:
    """Choose an image URL to use as diary cover if available."""
    if diary.media_urls and diary.media_types:
        for url, media_type in zip(diary.media_urls, diary.media_types):
            if media_type == DiaryMediaType.IMAGE:
                return url
    return None


def _build_region_summary(diary, region=None) -> RegionSummary:
    """Build RegionSummary using loaded relationship when possible."""
    region_obj = region or getattr(diary, "region", None)
    if region_obj is not None:
        return RegionSummary.model_validate(region_obj)

    region_id = getattr(diary, "region_id", 0) or 0
    return RegionSummary(
        id=region_id,
        name="未知地点",
        type="scenic",
        city=None,
    )


_PREVIEW_MAX_LENGTH = 160


def _extract_content_preview(diary, max_length: int = _PREVIEW_MAX_LENGTH) -> str:
    """Generate a plain-text preview snippet from diary content."""
    content = getattr(diary, "content", "") or ""

    if not content and getattr(diary, "is_compressed", False) and getattr(diary, "compressed_content", None):
        try:
            content = compression_service.decompress_content(
                diary.compressed_content,
                getattr(diary, "is_compressed", False),
            )
        except ValueError:
            content = ""

    if not content:
        return ""

    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_length:
        return text[:max_length].rstrip() + "…"
    return text


# ===== Diary CRUD Endpoints =====

@router.post("", response_model=DiaryCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_diary(
    *,
    title: str = Form(...),
    content: str = Form(...),
    region_id: int = Form(...),
    current_user: User = Depends(deps.get_current_user),
    service: DiaryService = Depends(_get_diary_service),
    status_value: DiaryStatus = Form(DiaryStatus.PUBLISHED),
    tags: Optional[str] = Form(None, description="JSON array of tag strings"),
    media_manifest: Optional[str] = Form(
        None, description="JSON array describing uploaded media placeholders"
    ),
    media_files: List[UploadFile] = File(default_factory=list),
) -> DiaryCreateResponse:
    """
    Create a new diary.
    
    Supports:
    - Automatic content compression
    - Media URLs (images/videos)
    - Tags for categorization
    - Draft or published status
    """
    # Validate and normalize basic fields
    title_value = title.strip()
    content_value = content.rstrip()

    # Parse tags JSON array if provided
    tags_value: List[str] = []
    if tags:
        try:
            parsed_tags = json.loads(tags)
            if not isinstance(parsed_tags, list):
                raise ValueError
            tags_value = [str(tag).strip() for tag in parsed_tags if str(tag).strip()]
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tags format. Expecting JSON array of strings.",
            )

    # Parse media manifest metadata
    manifest_items: List[DiaryMediaPlaceholder] = []
    if media_manifest:
        try:
            parsed_manifest = json.loads(media_manifest)
            if not isinstance(parsed_manifest, list):
                raise ValueError
            for entry in parsed_manifest:
                manifest_items.append(DiaryMediaPlaceholder.model_validate(entry))
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid media manifest: {exc}",
            )

    if len(media_files) != len(manifest_items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Media files count does not match manifest entries.",
        )

    request_payload = DiaryCreateRequest(
        title=title_value,
        content=content_value,
        region_id=region_id,
        tags=tags_value,
        media_placeholders=manifest_items,
        status=status_value,
    )

    # Build pending media uploads with in-memory data
    pending_media: List[PendingDiaryMedia] = []
    for placeholder, upload in zip(manifest_items, media_files):
        try:
            file_bytes = await upload.read()
        finally:
            await upload.close()

        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file '{upload.filename}' is empty.",
            )

        media_type = placeholder.media_type
        content_type_value = (
            placeholder.content_type
            or upload.content_type
            or ("image/png" if media_type == DiaryMediaType.IMAGE else "video/mp4")
        )

        filename_value = placeholder.filename or upload.filename or "media"

        pending_media.append(
            PendingDiaryMedia(
                placeholder=placeholder.placeholder,
                media_type=media_type,
                filename=filename_value,
                content_type=content_type_value,
                data=file_bytes,
            )
        )

    diary, compression_stats = await service.create_diary(
        user_id=current_user.id,
        request=request_payload,
        media_uploads=pending_media,
    )
    
    return DiaryCreateResponse(
        id=diary.id,
        title=diary.title,
        created_at=diary.created_at,
        compressed=compression_stats['compressed'],
        compression_ratio=compression_stats['ratio'],
    )


# ===== Diary Recommendations =====

@router.get("/recommendations", response_model=DiaryRecommendationResponse)
async def recommend_diaries(
    *,
    limit: int = Query(20, ge=1, le=50, description="Maximum number of items to return"),
    sort_by: str = Query("hybrid", description="Sorting strategy: hybrid, popularity, rating, latest"),
    interests: List[str] = Query(default_factory=list, description="Interest tags to boost matches"),
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    service: DiaryService = Depends(_get_diary_service),
) -> DiaryRecommendationResponse:
    """
    Get personalized diary recommendations.

    Supports multiple sorting strategies:
    - hybrid: Balanced score using popularity, rating, and interest matching
    - popularity: Sort by view count and engagement
    - rating: Sort by average user rating
    - latest: Sort by creation date (newest first)
    """
    import time
    start_time = time.time()

    # Get recommendations
    recommendations = await service.recommend_diaries(
        limit=limit,
        sort_by=sort_by,
        interests=interests,
        region_id=region_id,
    )

    execution_time = int((time.time() - start_time) * 1000)

    # Convert to response format
    items = []
    for diary, score in recommendations:
        cover_image = _select_cover_image(diary)
        region_summary = _build_region_summary(diary)

        diary_item = DiaryListItem(
            id=diary.id,
            title=diary.title,
            content_preview=_extract_content_preview(diary),
            author=UserSummary.model_validate(diary.author),
            region=region_summary,
            cover_image=cover_image,
            tags=diary.tags,
            popularity=diary.popularity,
            rating=diary.rating,
            ratings_count=diary.ratings_count,
            comments_count=diary.comments_count,
            status=diary.status,
            created_at=diary.created_at,
            updated_at=diary.updated_at,
        )

        # Calculate interest matches
        interest_matches = []
        if interests and diary.tags:
            interest_matches = list(set(diary.tags) & set(interests))

        items.append(DiaryRecommendationItem(
            diary=diary_item,
            score=round(score, 3),
            interest_matches=interest_matches,
        ))

    return DiaryRecommendationResponse(
        items=items,
        total=len(items),
        limit=limit,
        total_candidates=len(recommendations),
        sort_by=sort_by,
        generated_at=datetime.now(),
        page=1,
        page_size=limit,
        query=None,
        interests=interests,
        execution_time_ms=execution_time,
    )


@router.get("/{diary_id}", response_model=DiaryDetail)
async def get_diary(
    *,
    diary_id: int,
    service: DiaryService = Depends(_get_diary_service),
) -> DiaryDetail:
    """
    Get diary details by ID.
    
    Content is automatically decompressed if stored compressed.
    """
    diary = await service.get_diary(diary_id, decompress=True)
    
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diary {diary_id} not found"
        )

    ordered_media_items = sorted(diary.media_items, key=lambda media: media.id)
    media_items_payload = [
        DiaryMediaItem(
            id=media.id,
            placeholder=media.placeholder,
            filename=media.filename,
            content_type=media.content_type,
            media_type=media.media_type,
            url=f"{settings.api_prefix}{settings.api_v1_prefix}/diaries/{diary.id}/media/{media.id}",
            original_size=media.original_size,
            compressed_size=media.compressed_size,
            is_compressed=media.is_compressed,
        )
        for media in ordered_media_items
    ]
    if media_items_payload:
        media_urls = [item.url for item in media_items_payload]
        media_types = [item.media_type for item in media_items_payload]
    else:
        media_urls = diary.media_urls
        media_types = diary.media_types
    
    # Build response
    region_summary = _build_region_summary(diary)

    return DiaryDetail(
        id=diary.id,
        title=diary.title,
        content_preview=_extract_content_preview(diary, max_length=300),
        content=diary.content,
        author=UserSummary.model_validate(diary.author),
        region=region_summary,
        media_urls=media_urls,
        media_types=media_types,
        media_items=media_items_payload,
        tags=diary.tags,
        popularity=diary.popularity,
        rating=diary.rating,
        ratings_count=diary.ratings_count,
        comments_count=diary.comments_count,
        status=diary.status,
        is_compressed=diary.is_compressed,
        created_at=diary.created_at,
        updated_at=diary.updated_at,
    )


@router.get("/{diary_id}/media/{media_id}")
async def download_diary_media(
    *,
    diary_id: int,
    media_id: int,
    service: DiaryService = Depends(_get_diary_service),
):
    """Stream a diary media asset (image/video) inline."""

    result = await service.get_diary_media_payload(diary_id, media_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )

    media, payload = result
    headers = {
        "Content-Length": str(len(payload)),
        "Content-Disposition": _build_content_disposition(media.filename, "inline"),
    }

    return StreamingResponse(
        iter([payload]),
        media_type=media.content_type,
        headers=headers,
    )


@router.put("/{diary_id}", response_model=DiaryDetail)
async def update_diary(
    *,
    diary_id: int,
    request: DiaryUpdateRequest,
    current_user: User = Depends(deps.get_current_user),
    service: DiaryService = Depends(_get_diary_service),
) -> DiaryDetail:
    """
    Update an existing diary.
    
    Requires:
    - User must be the diary author
    - Content will be re-compressed if changed
    """
    try:
        diary = await service.update_diary(
            diary_id=diary_id,
            user_id=current_user.id,
            request=request,
        )
        
        if not diary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diary {diary_id} not found"
            )
        
        # Reload with relationships
        diary = await service.get_diary(diary_id, decompress=True)

        ordered_media_items = sorted(diary.media_items, key=lambda media: media.id)
        media_items_payload = [
            DiaryMediaItem(
                id=media.id,
                placeholder=media.placeholder,
                filename=media.filename,
                content_type=media.content_type,
                media_type=media.media_type,
                url=f"{settings.api_prefix}{settings.api_v1_prefix}/diaries/{diary.id}/media/{media.id}",
                original_size=media.original_size,
                compressed_size=media.compressed_size,
                is_compressed=media.is_compressed,
            )
            for media in ordered_media_items
        ]

        if media_items_payload:
            media_urls = [item.url for item in media_items_payload]
            media_types = [item.media_type for item in media_items_payload]
        else:
            media_urls = diary.media_urls
            media_types = diary.media_types

        region_summary = _build_region_summary(diary)

        return DiaryDetail(
            id=diary.id,
            title=diary.title,
            content_preview=_extract_content_preview(diary, max_length=300),
            content=diary.content,
            author=UserSummary.model_validate(diary.author),
            region=region_summary,
            media_urls=media_urls,
            media_types=media_types,
            media_items=media_items_payload,
            tags=diary.tags,
            popularity=diary.popularity,
            rating=diary.rating,
            ratings_count=diary.ratings_count,
            comments_count=diary.comments_count,
            status=diary.status,
            is_compressed=diary.is_compressed,
            created_at=diary.created_at,
            updated_at=diary.updated_at,
        )
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{diary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diary(
    *,
    diary_id: int,
    current_user: User = Depends(deps.get_current_user),
    service: DiaryService = Depends(_get_diary_service),
):
    """
    Delete a diary.
    
    Requires:
    - User must be the diary author
    - Cascades to ratings, views, and animations
    """
    try:
        success = await service.delete_diary(
            diary_id=diary_id,
            user_id=current_user.id,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diary {diary_id} not found"
            )
            
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


# ===== Diary List and Search =====

@router.get("", response_model=dict)
async def list_diaries(
    *,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    region_id: Optional[int] = Query(None, description="Filter by region"),
    author_id: Optional[UUID] = Query(None, description="Filter by author"),
    status: Optional[DiaryStatus] = Query(None, description="Filter by status"),
    interests: List[str] = Query(default=[], description="Filter by tags"),
    q: Optional[str] = Query(None, description="Search query"),
    service: DiaryService = Depends(_get_diary_service),
) -> dict:
    """
    List diaries with filtering and pagination.
    
    Supports:
    - Pagination
    - Filter by region, author, status
    - Tag-based filtering (interests)
    - Keyword search (title and content)
    """
    from app.schemas.diary import DiaryListParams
    
    params = DiaryListParams(
        page=page,
        page_size=page_size,
        region_id=region_id,
        author_id=author_id,
        status=status,
        interests=interests,
        q=q,
        sort_by='latest',
    )
    
    diaries, total = await service.list_diaries(params)

    items = []
    for diary in diaries:
        cover_image = _select_cover_image(diary)
        region_summary = _build_region_summary(diary)

        items.append(DiaryListItem(
            id=diary.id,
            title=diary.title,
            content_preview=_extract_content_preview(diary),
            author=UserSummary.model_validate(diary.author),
            region=region_summary,
            cover_image=cover_image,
            tags=diary.tags,
            popularity=diary.popularity,
            rating=diary.rating,
            ratings_count=diary.ratings_count,
            comments_count=diary.comments_count,
            status=diary.status,
            created_at=diary.created_at,
            updated_at=diary.updated_at,
        ))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }





# ===== View and Rating =====

@router.get("/{diary_id}/ratings", response_model=DiaryRatingListResponse)
async def list_diary_ratings(
    *,
    diary_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: Optional[User] = Depends(deps.get_optional_current_user),
    service: DiaryService = Depends(_get_diary_service),
) -> DiaryRatingListResponse:
    """Return paginated diary ratings with aggregate statistics."""
    try:
        result = await service.get_diary_ratings(
            diary_id=diary_id,
            page=page,
            page_size=page_size,
            current_user_id=current_user.id if current_user else None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    items = [
        DiaryRatingItem.model_validate(rating, from_attributes=True)
        for rating in result["items"]
    ]

    current_user_rating = (
        DiaryRatingItem.model_validate(result["current_user_rating"], from_attributes=True)
        if result["current_user_rating"]
        else None
    )

    stats = result["stats"]

    return DiaryRatingListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        average_score=stats["average"],
        score_distribution=stats["distribution"],
        comments_count=stats["comments_count"],
        current_user_rating=current_user_rating,
    )


@router.post("/{diary_id}/view", status_code=status.HTTP_204_NO_CONTENT)
async def record_diary_view(
    *,
    diary_id: int,
    request: Request,
    view_request: DiaryViewRequest = None,
    current_user: Optional[User] = Depends(deps.get_optional_current_user),
    service: DiaryService = Depends(_get_diary_service),
):
    """
    Record a diary view to update popularity.
    
    Tracks:
    - User ID (if authenticated)
    - IP address (for anonymous users)
    - User agent
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get('user-agent')

    success = await service.record_view(
        diary_id=diary_id,
        user_id=current_user.id if current_user else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diary {diary_id} not found"
        )


@router.post("/{diary_id}/rate", response_model=DiaryRatingResponse)
async def rate_diary(
    *,
    diary_id: int,
    request: DiaryRatingRequest,
    current_user: User = Depends(deps.get_current_user),
    service: DiaryService = Depends(_get_diary_service),
) -> DiaryRatingResponse:
    """
    Rate a diary (1-5 stars) with optional comment.
    
    Features:
    - One rating per user per diary
    - Updates existing rating if already rated
    - Automatically recalculates diary's average rating
    """
    try:
        rating = await service.rate_diary(
            diary_id=diary_id,
            user_id=current_user.id,
            score=request.score,
            comment=request.comment,
        )
        
        return DiaryRatingResponse(
            id=rating.id,
            diary_id=rating.diary_id,
            user_id=rating.user_id,
            score=rating.score,
            comment=rating.comment,
            created_at=rating.created_at,
            updated_at=rating.updated_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ===== Animation Generation (AIGC) =====

@router.post("/{diary_id}/generate-animation", response_model=DiaryAnimationResponse)
async def generate_diary_animation(
    *,
    diary_id: int,
    request: AnimationGenerateRequest,
    service: DiaryService = Depends(_get_diary_service),
) -> DiaryAnimationResponse:
    """
    Generate travel animation using AIGC (wan2.5).
    
    Process:
    1. Extracts images from diary
    2. Uses title and content as description
    3. Calls wan2.5 API (async task)
    4. Returns task ID for status polling
    
    Note: This is a placeholder. Actual wan2.5 integration needed.
    """
    generation_params = {
        'style': request.style,
        'duration': request.duration,
        'custom_description': request.custom_description,
    }
    
    try:
        animation = await service.create_animation_task(
            diary_id=diary_id,
            generation_params=generation_params,
        )
        
        return DiaryAnimationResponse(
            id=animation.id,
            diary_id=animation.diary_id,
            status=animation.status,
            progress=animation.progress,
            video_url=animation.video_url,
            thumbnail_url=animation.thumbnail_url,
            error_message=animation.error_message,
            created_at=animation.created_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{diary_id}/animations", response_model=List[DiaryAnimationResponse])
async def get_diary_animations(
    *,
    diary_id: int,
    service: DiaryService = Depends(_get_diary_service),
) -> List[DiaryAnimationResponse]:
    """Get all animations for a diary."""
    animations = await service.get_diary_animations(diary_id)
    
    return [
        DiaryAnimationResponse(
            id=anim.id,
            diary_id=anim.diary_id,
            status=anim.status,
            progress=anim.progress,
            video_url=anim.video_url,
            thumbnail_url=anim.thumbnail_url,
            error_message=anim.error_message,
            created_at=anim.created_at,
        )
        for anim in animations
    ]


# ===== User's Diaries =====

@router.get("/users/{user_id}/diaries", response_model=dict)
async def get_user_diaries(
    *,
    user_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[DiaryStatus] = Query(None),
    service: DiaryService = Depends(_get_diary_service),
) -> dict:
    """Get all diaries by a specific user."""
    diaries, total = await service.get_user_diaries(
        user_id=user_id,
        page=page,
        page_size=page_size,
        status=status,
    )
    
    items = []
    for diary in diaries:
        cover_image = _select_cover_image(diary)
        region_summary = _build_region_summary(diary)

        items.append(DiaryListItem(
            id=diary.id,
            title=diary.title,
            content_preview=_extract_content_preview(diary),
            author=UserSummary.model_validate(diary.author),
            region=region_summary,
            cover_image=cover_image,
            tags=diary.tags,
            popularity=diary.popularity,
            rating=diary.rating,
            ratings_count=diary.ratings_count,
            comments_count=diary.comments_count,
            status=diary.status,
            created_at=diary.created_at,
            updated_at=diary.updated_at,
        ))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ===== Diary Search =====

@router.get("/search", response_model=DiarySearchResponse)
async def search_diaries(
    *,
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    region_id: Optional[int] = Query(None, description="Filter by region"),
    service: DiaryService = Depends(_get_diary_service),
) -> DiarySearchResponse:
    """
    Full-text search diaries using FTS5.
    
    Features:
    - BM25 relevance scoring
    - Chinese text support
    - Field-specific matching (title, content, tags)
    - Region filtering
    """
    import time
    start_time = time.time()
    
    results = await service.search_diaries(
        query=q,
        limit=limit,
        region_id=region_id,
    )
    
    execution_time = (time.time() - start_time) * 1000  # ms
    
    region_ids = [getattr(diary, "region_id", None) for diary, _, _ in results]
    region_map = await service.get_region_map([rid for rid in region_ids if rid])

    items = []
    for diary, relevance_score, matched_fields in results:
        cover_image = _select_cover_image(diary)
        region_summary = _build_region_summary(diary, region_map.get(getattr(diary, "region_id", 0)))

        diary_item = DiaryListItem(
            id=diary.id,
            title=diary.title,
            content_preview=_extract_content_preview(diary),
            author=UserSummary.model_validate(diary.author),
            region=region_summary,
            cover_image=cover_image,
            tags=diary.tags,
            popularity=diary.popularity,
            rating=diary.rating,
            ratings_count=diary.ratings_count,
            comments_count=diary.comments_count,
            status=diary.status,
            created_at=diary.created_at,
            updated_at=diary.updated_at,
        )
        
        items.append(DiarySearchResult(
            diary=diary_item,
            relevance_score=relevance_score,
            matched_fields=matched_fields,
        ))
    
    return DiarySearchResponse(
        items=items,
        query=q,
        total=len(items),
        execution_time_ms=execution_time,
    )