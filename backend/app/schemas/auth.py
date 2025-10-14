"""Authentication related schemas."""

from __future__ import annotations

from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field

from .user import UserPublic


class LoginRequest(BaseModel):
	"""Credentials submitted for login."""

	identifier: str = Field(..., description="Username")
	password: str = Field(..., min_length=8, max_length=128)


class TokenPair(BaseModel):
	"""Access and refresh token pair."""

	access_token: str
	refresh_token: str
	token_type: Literal["bearer"] = "bearer"
	expires_in: int = Field(..., description="Seconds until the access token expires")
	refresh_expires_in: int = Field(..., description="Seconds until the refresh token expires")
	issued_at: datetime
	user: UserPublic


class RefreshRequest(BaseModel):
	"""Refresh token payload."""

	refresh_token: str = Field(..., min_length=20)


class LogoutRequest(BaseModel):
	"""Logout payload for explicit refresh revocation."""

	refresh_token: str = Field(..., min_length=20)
