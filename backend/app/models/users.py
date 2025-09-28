"""User related models."""

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship

from .base import BaseModel, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from .diaries import Diary


class User(TimestampMixin, BaseModel, table=True):
    """System user."""

    __tablename__ = "users"

    username: str = Field(index=True, unique=True)
    display_name: str
    email: Optional[str] = Field(default=None, index=True)
    interests: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )

    diaries: List["Diary"] = Relationship(back_populates="author")