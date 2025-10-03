"""Pydantic schemas for diary API requests and responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import DiaryMediaType, DiaryStatus


# ===== User Summary =====
class UserSummary(BaseModel):
    """Simplified user information for diary responses."""
    
    id: int
    username: str
    display_name: str
    
    class Config:
        from_attributes = True


# ===== Region Summary =====
class RegionSummary(BaseModel):
    """Simplified region information for diary responses."""
    
    id: int
    name: str
    type: str
    city: Optional[str] = None
    
    class Config:
        from_attributes = True


# ===== Diary Request Schemas =====
class DiaryCreateRequest(BaseModel):
    """Request schema for creating a new diary."""
    
    title: str = Field(..., min_length=1, max_length=200)
    summary: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=10)
    region_id: int = Field(..., gt=0)
    tags: List[str] = Field(default_factory=list, max_length=20)
    media_urls: List[str] = Field(default_factory=list, max_length=50)
    media_types: List[DiaryMediaType] = Field(default_factory=list, max_length=50)
    status: DiaryStatus = Field(default=DiaryStatus.PUBLISHED)
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and clean tags."""
        # Remove empty tags and duplicates
        cleaned = [tag.strip() for tag in v if tag.strip()]
        return list(dict.fromkeys(cleaned))[:20]  # Max 20 unique tags
    
    @field_validator('media_types')
    @classmethod
    def validate_media_match(cls, v: List[DiaryMediaType], info) -> List[DiaryMediaType]:
        """Ensure media_urls and media_types have same length."""
        if 'media_urls' in info.data:
            media_urls = info.data['media_urls']
            if len(v) != len(media_urls):
                raise ValueError('media_urls and media_types must have the same length')
        return v


class DiaryUpdateRequest(BaseModel):
    """Request schema for updating an existing diary."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    summary: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=10)
    region_id: Optional[int] = Field(None, gt=0)
    tags: Optional[List[str]] = Field(None, max_length=20)
    media_urls: Optional[List[str]] = Field(None, max_length=50)
    media_types: Optional[List[DiaryMediaType]] = Field(None, max_length=50)
    status: Optional[DiaryStatus] = None


# ===== Diary Response Schemas =====
class DiaryListItem(BaseModel):
    """Simplified diary information for list views."""
    
    id: int
    title: str
    summary: Optional[str]
    author: UserSummary
    region: RegionSummary
    cover_image: Optional[str] = None  # First image from media_urls
    tags: List[str]
    popularity: int
    rating: float
    ratings_count: int
    comments_count: int
    status: DiaryStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DiaryDetail(BaseModel):
    """Complete diary information including content."""
    
    id: int
    title: str
    summary: Optional[str]
    content: str  # Decompressed content
    author: UserSummary
    region: RegionSummary
    media_urls: List[str]
    media_types: List[DiaryMediaType]
    tags: List[str]
    popularity: int
    rating: float
    ratings_count: int
    comments_count: int
    status: DiaryStatus
    is_compressed: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DiaryCreateResponse(BaseModel):
    """Response after creating a diary."""
    
    id: int
    title: str
    created_at: datetime
    compressed: bool
    compression_ratio: Optional[float] = None


# ===== Diary Rating Schemas =====
class DiaryRatingRequest(BaseModel):
    """Request schema for rating a diary."""
    
    score: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)


class DiaryRatingResponse(BaseModel):
    """Response schema for diary rating."""
    
    id: int
    diary_id: int
    user_id: int
    score: int
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===== Diary View Schema =====
class DiaryViewRequest(BaseModel):
    """Request schema for recording a view."""
    
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# ===== Recommendation Schemas =====
class DiaryRecommendationItem(BaseModel):
    """Diary item with recommendation score."""
    
    diary: DiaryListItem
    score: float = Field(..., description="Recommendation score (0.0-1.0)")
    interest_matches: List[str] = Field(default_factory=list, description="Matched interests between the user and diary tags")


class DiaryRecommendationResponse(BaseModel):
    """Response schema for diary recommendations."""
    
    items: List[DiaryRecommendationItem]
    total: int = Field(..., ge=0, description="Number of recommendations returned")
    limit: int = Field(..., ge=1, description="Requested number of recommendations")
    total_candidates: int = Field(..., ge=0, description="Total candidate diaries evaluated")
    sort_by: str
    generated_at: datetime
    page: int = Field(1, ge=1, description="Current page index (always 1 for recommendations)")
    page_size: int = Field(..., ge=1, description="Page size, mirrors the requested limit")
    query: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    execution_time_ms: int = Field(..., ge=0)


# ===== Search Schemas =====
class DiarySearchResult(BaseModel):
    """Search result with relevance score."""
    
    diary: DiaryListItem
    relevance_score: float
    matched_fields: List[str]
    highlights: Optional[dict] = None  # Field -> highlighted snippet


class DiarySearchResponse(BaseModel):
    """Response schema for diary search."""
    
    items: List[DiarySearchResult]
    query: str
    total: int
    execution_time_ms: float


# ===== Animation Schemas =====
class AnimationGenerateRequest(BaseModel):
    """Request schema for generating travel animation."""
    
    style: Optional[str] = Field('travel', description="Animation style")
    duration: Optional[int] = Field(30, ge=5, le=120, description="Duration in seconds")
    custom_description: Optional[str] = Field(None, max_length=500)


class DiaryAnimationResponse(BaseModel):
    """Response schema for diary animation."""
    
    id: int
    diary_id: int
    status: str
    progress: int
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===== Query Parameters =====
class DiaryListParams(BaseModel):
    """Query parameters for listing diaries."""
    
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=50)
    sort_by: str = Field('latest', pattern='^(latest|popularity|rating|hybrid)$')
    region_id: Optional[int] = Field(None, gt=0)
    author_id: Optional[int] = Field(None, gt=0)
    status: Optional[DiaryStatus] = None
    interests: List[str] = Field(default_factory=list)
    q: Optional[str] = None  # Search query
