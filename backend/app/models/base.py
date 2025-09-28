"""Base declarations for SQLModel models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class TimestampMixin(SQLModel):
    """Reusable timestamp fields."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BaseModel(SQLModel):
    """Base class to enforce common config."""

    id: Optional[int] = Field(default=None, primary_key=True)

    class Config:
        arbitrary_types_allowed = True
        use_enum_values = True
