"""API endpoints for diary management."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.enums import DiaryStatus
from app.repositories.diaries import DiaryRepository
from app.services.diary import DiaryService
from app.schemas.diary import (
    DiaryCreateRequest,
    DiaryUpdateRequest,
    DiaryDetail,
    DiaryListItem,
    DiaryCreateResponse,
    DiaryRatingRequest,
    DiaryRatingResponse,
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


# ===== Diary CRUD Endpoints =====

@router.post("", response_model=DiaryCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_diary(
    *,
    request: DiaryCreateRequest,
    current_user_id: int = 1,  # TODO: Get from auth
    service: DiaryService = Depends(_get_diary_service),
) -> DiaryCreateResponse:
    """
    Create a new diary.
    
    Supports:
    - Automatic content compression
    - Media URLs (images/videos)
    - Tags for categorization
    - Draft or published status
    """
    diary, compression_stats = await service.create_diary(
        user_id=current_user_id,
        request=request,
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
        # Get cover image
        cover_image = diary.media_urls[0] if diary.media_urls else None

        diary_item = DiaryListItem(
            id=diary.id,
            title=diary.title,
            summary=diary.summary,
            author=UserSummary.model_validate(diary.author),
            region=RegionSummary(
                id=diary.region_id,
                name="",
                type="scenic",
                city=None,
            ),
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
    
    # Build response
    return DiaryDetail(
        id=diary.id,
        title=diary.title,
        summary=diary.summary,
        content=diary.content,
        author=UserSummary.model_validate(diary.author),
        region=RegionSummary(
            id=diary.region_id,
            name="",  # Will be loaded separately if needed
            type="scenic",
            city=None,
        ),
        media_urls=diary.media_urls,
        media_types=diary.media_types,
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


@router.put("/{diary_id}", response_model=DiaryDetail)
async def update_diary(
    *,
    diary_id: int,
    request: DiaryUpdateRequest,
    current_user_id: int = 1,  # TODO: Get from auth
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
            user_id=current_user_id,
            request=request,
        )
        
        if not diary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diary {diary_id} not found"
            )
        
        # Reload with relationships
        diary = await service.get_diary(diary_id, decompress=True)
        
        return DiaryDetail(
            id=diary.id,
            title=diary.title,
            summary=diary.summary,
            content=diary.content,
            author=UserSummary.model_validate(diary.author),
            region=RegionSummary(
                id=diary.region_id,
                name="",
                type="scenic",
                city=None,
            ),
            media_urls=diary.media_urls,
            media_types=diary.media_types,
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
    current_user_id: int = 1,  # TODO: Get from auth
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
            user_id=current_user_id,
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
    author_id: Optional[int] = Query(None, description="Filter by author"),
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
    - Keyword search (title and summary)
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
        cover_image = diary.media_urls[0] if diary.media_urls else None
        
        items.append(DiaryListItem(
            id=diary.id,
            title=diary.title,
            summary=diary.summary,
            author=UserSummary.model_validate(diary.author),
            region=RegionSummary(
                id=diary.region_id,
                name="",
                type="scenic",
                city=None,
            ),
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

@router.post("/{diary_id}/view", status_code=status.HTTP_204_NO_CONTENT)
async def record_diary_view(
    *,
    diary_id: int,
    request: Request,
    view_request: DiaryViewRequest = None,
    current_user_id: Optional[int] = None,  # Optional for anonymous views
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
        user_id=current_user_id,
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
    current_user_id: int = 1,  # TODO: Get from auth
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
            user_id=current_user_id,
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
    user_id: int,
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
        cover_image = diary.media_urls[0] if diary.media_urls else None
        
        items.append(DiaryListItem(
            id=diary.id,
            title=diary.title,
            summary=diary.summary,
            author=UserSummary.model_validate(diary.author),
            region=RegionSummary(
                id=diary.region_id,
                name="",
                type="scenic",
                city=None,
            ),
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
    
    items = []
    for diary, relevance_score, matched_fields in results:
        # Get cover image
        cover_image = diary.media_urls[0] if diary.media_urls else None
        
        diary_item = DiaryListItem(
            id=diary.id,
            title=diary.title,
            summary=diary.summary,
            author=UserSummary.model_validate(diary.author),
            region=RegionSummary(
                id=diary.region_id,
                name="",
                type="scenic",
                city=None,
            ),
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



