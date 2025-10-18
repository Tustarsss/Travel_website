"""Pydantic schemas for user resources."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class UserBase(BaseModel):
	"""Shared user fields."""

	username: str = Field(..., min_length=3, max_length=50)
	interests: List[str] = Field(default_factory=list, max_length=20)

	@field_validator("username")
	@classmethod
	def normalize_username(cls, value: str) -> str:
		return value.strip()



class UserCreateRequest(UserBase):
	"""Payload for registering a new user."""

	password: str = Field(..., min_length=8, max_length=128)


class UserUpdateRequest(BaseModel):
	"""Payload for updating user profile."""

	interests: Optional[List[str]] = Field(default=None, max_length=20)


class UserPublic(UserBase):
	"""Public-facing user representation."""

	id: int
	is_active: bool
	last_login_at: Optional[datetime]
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True
