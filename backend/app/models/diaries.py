"""Diary related models."""

from typing import List, Optional

from sqlalchemy import Column, JSON, LargeBinary
from sqlmodel import Field, Relationship

from .base import BaseModel, TimestampMixin
from .enums import DiaryMediaType, DiaryStatus
from .users import User


class Diary(TimestampMixin, BaseModel, table=True):
    """Travel diary entity."""

    __tablename__ = "diaries"

    user_id: int = Field(foreign_key="users.id", index=True)
    region_id: int = Field(foreign_key="regions.id", index=True)
    title: str
    summary: Optional[str] = None
    content: str
    compressed_content: Optional[bytes] = Field(  # stored compressed blob
        default=None, sa_column=Column(LargeBinary)
    )
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
    popularity: int = Field(default=0, ge=0)
    rating: float = Field(default=0.0, ge=0.0, le=5.0)
    ratings_count: int = Field(default=0, ge=0)
    status: DiaryStatus = Field(default=DiaryStatus.PUBLISHED)

    author: User = Relationship(back_populates="diaries")
    ratings: List["DiaryRating"] = Relationship(back_populates="diary")


class DiaryRating(TimestampMixin, BaseModel, table=True):
    """User rating for a diary."""

    __tablename__ = "diary_ratings"

    diary_id: int = Field(foreign_key="diaries.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    score: int = Field(ge=1, le=5)
    comment: Optional[str] = None

    diary: Diary = Relationship(back_populates="ratings")
