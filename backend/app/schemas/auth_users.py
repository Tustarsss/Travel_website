"""Pydantic schemas for fastapi-users integration."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi_users import schemas as fu_schemas
from pydantic import EmailStr, Field, field_validator


class UserRead(fu_schemas.BaseUser[UUID]):
    """User read schema extends fastapi-users base with extra fields."""

    username: str
    interests: List[str] = []
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserCreate(fu_schemas.BaseUserCreate):
    """User create schema with email+password+username."""

    username: str = Field(..., min_length=3, max_length=50)
    interests: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.strip()



class UserUpdate(fu_schemas.BaseUserUpdate):
    """User update schema with optional profile fields."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    interests: Optional[List[str]] = Field(default=None, max_length=20)
