"""Diary related models."""

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, JSON, LargeBinary, UniqueConstraint
from sqlmodel import Field, Relationship

from .base import BaseModel, TimestampMixin
from .enums import DiaryMediaType, DiaryStatus
from .users import User

if TYPE_CHECKING:
    from .locations import Region


class Diary(TimestampMixin, BaseModel, table=True):
    """Travel diary entity."""

    __tablename__ = "diaries"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    region_id: int = Field(foreign_key="regions.id", index=True)
    title: str = Field(index=True)
    summary: Optional[str] = None
    content: str
    compressed_content: Optional[bytes] = Field(  # stored compressed blob
        default=None, sa_column=Column(LargeBinary)
    )
    is_compressed: bool = Field(default=False)  # 标识内容是否已压缩
    media_urls: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    media_types: List[DiaryMediaType] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    popularity: int = Field(default=0, ge=0)  # 浏览量
    rating: float = Field(default=0.0, ge=0.0, le=5.0)  # 平均评分
    ratings_count: int = Field(default=0, ge=0)  # 评分人数
    comments_count: int = Field(default=0, ge=0)  # 评论数
    status: DiaryStatus = Field(default=DiaryStatus.PUBLISHED)

    # Relationships
    author: User = Relationship(back_populates="diaries")
    region: "Region" = Relationship(back_populates="diaries")
    ratings: List["DiaryRating"] = Relationship(back_populates="diary", cascade_delete=True)
    views: List["DiaryView"] = Relationship(back_populates="diary", cascade_delete=True)
    animations: List["DiaryAnimation"] = Relationship(back_populates="diary", cascade_delete=True)
    media_items: List["DiaryMedia"] = Relationship(
        back_populates="diary",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class DiaryMedia(TimestampMixin, BaseModel, table=True):
    """Binary media (images/videos) associated with diaries."""

    __tablename__ = "diary_media"

    diary_id: int = Field(foreign_key="diaries.id", index=True)
    placeholder: str = Field(max_length=100, index=True)
    filename: str = Field(max_length=255)
    content_type: str = Field(max_length=100)
    media_type: DiaryMediaType = Field()
    original_size: int = Field(ge=0)
    compressed_size: int = Field(ge=0)
    is_compressed: bool = Field(default=False)
    data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))

    diary: "Diary" = Relationship(back_populates="media_items")


class DiaryRating(TimestampMixin, BaseModel, table=True):
    """User rating for a diary."""

    __tablename__ = "diary_ratings"
    __table_args__ = (
        UniqueConstraint("diary_id", "user_id", name="uq_diary_user_rating"),
    )

    diary_id: int = Field(foreign_key="diaries.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    score: int = Field(ge=1, le=5)
    comment: Optional[str] = None

    diary: Diary = Relationship(back_populates="ratings")
    user: User = Relationship(back_populates="ratings")


class DiaryView(TimestampMixin, BaseModel, table=True):
    """Diary view tracking for popularity calculation."""

    __tablename__ = "diary_views"

    diary_id: int = Field(foreign_key="diaries.id", index=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id", index=True)
    ip_address: Optional[str] = Field(default=None, max_length=45)  # IPv6 support
    user_agent: Optional[str] = Field(default=None, max_length=255)

    diary: Diary = Relationship(back_populates="views")


class DiaryAnimation(TimestampMixin, BaseModel, table=True):
    """AIGC generated travel animation."""

    __tablename__ = "diary_animations"

    diary_id: int = Field(foreign_key="diaries.id", index=True)
    generation_params: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str = Field(default="pending")  # pending/processing/completed/failed
    progress: int = Field(default=0, ge=0, le=100)  # 生成进度百分比
    error_message: Optional[str] = None
    task_id: Optional[str] = None  # 外部API任务ID

    diary: Diary = Relationship(back_populates="animations")
