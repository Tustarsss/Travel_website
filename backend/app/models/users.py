"""User related models."""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship

from .base import BaseModel, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from .diaries import Diary
    from .sessions import UserSession


class User(TimestampMixin, BaseModel, table=True):
    """System user."""

    __tablename__ = "users"

    username: str = Field(index=True, unique=True)
    display_name: str
    hashed_password: str = Field(min_length=8, max_length=128, repr=False)
    is_active: bool = Field(default=True, index=True)
    last_login_at: Optional[datetime] = Field(default=None, index=True)
    interests: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )

    diaries: List["Diary"] = Relationship(back_populates="author")
    sessions: List["UserSession"] = Relationship(back_populates="user", cascade_delete=True)