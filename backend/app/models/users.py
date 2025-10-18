"""User related models compatible with fastapi-users."""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship

from .base import BaseModel, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from .diaries import Diary, DiaryRating


class User(TimestampMixin, BaseModel, table=True):
    """Application user table.

    This model is designed to be compatible with fastapi-users SQLAlchemy adapter.
    Required fields:
    - email (unique)
    - hashed_password
    - is_active
    - is_superuser
    - is_verified

    We also keep domain-specific fields such as username/interests.
    """

    __tablename__ = "users"

    # Override base id to use UUID for users
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # fastapi-users required fields
    email: str = Field(index=True, unique=True)
    hashed_password: str = Field(min_length=8, max_length=128, repr=False)
    is_active: bool = Field(default=True, index=True)
    is_superuser: bool = Field(default=False, index=True)
    is_verified: bool = Field(default=False, index=True)

    # project-specific fields
    username: str = Field(index=True, unique=True)
    last_login_at: Optional[datetime] = Field(default=None, index=True)
    interests: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )

    # relationships
    diaries: List["Diary"] = Relationship(back_populates="author")
    ratings: List["DiaryRating"] = Relationship(back_populates="user", cascade_delete=True)
    # Legacy refresh-token sessions removed; no sessions relationship