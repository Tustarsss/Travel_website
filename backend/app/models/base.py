"""Base declarations for SQLModel models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import SQLModel, Field
from pydantic import ConfigDict


def _now_utc() -> datetime:
    return datetime.now(UTC)


class TimestampMixin(SQLModel):
    """Reusable timestamp fields."""

    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class BaseModel(SQLModel):
    """Base class to enforce common config."""

    id: Optional[int] = Field(default=None, primary_key=True)

    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)
