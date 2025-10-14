"""User session model for refresh token persistence."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship

from .base import BaseModel, TimestampMixin
from .users import User


class UserSession(TimestampMixin, BaseModel, table=True):
	"""Persistent login session associated with a user."""

	__tablename__ = "user_sessions"

	user_id: int = Field(foreign_key="users.id", index=True)
	refresh_token_hash: str = Field(max_length=128, index=True)
	expires_at: datetime = Field(index=True)
	user_agent: Optional[str] = Field(default=None, max_length=255)
	ip_address: Optional[str] = Field(default=None, max_length=45)
	is_active: bool = Field(default=True, index=True)

	user: Optional[User] = Relationship(back_populates="sessions")
