"""Authentication and user session management services."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import status

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_token,
    verify_password,
    hash_password,
)
from app.models.sessions import UserSession
from app.models.users import User
from app.repositories.users import UserRepository, UserSessionRepository
from app.schemas.auth import TokenPair
from app.schemas.user import UserCreateRequest


class AuthServiceError(Exception):
    """Domain-specific error raised by the auth service."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class AuthService:
    """Service providing registration, login, and token lifecycle management."""

    def __init__(self, user_repo: UserRepository, session_repo: UserSessionRepository):
        self.user_repo = user_repo
        self.session_repo = session_repo

    async def register_user(self, payload: UserCreateRequest) -> User:
        """Create a new user account if the username is available."""

        normalized_username = payload.username.strip().lower()
        existing = await self.user_repo.get_by_username(normalized_username)
        if existing:
            raise AuthServiceError("用户名已被使用", status.HTTP_409_CONFLICT)

        hashed_pwd = hash_password(payload.password)

        user = User(
            username=normalized_username,
            display_name=payload.display_name.strip(),
            hashed_password=hashed_pwd,
            interests=payload.interests,
        )
        return await self.user_repo.create(user)

    async def authenticate_user(self, identifier: str, password: str) -> User:
        """Validate credentials using username and return the user instance."""

        identifier = identifier.strip().lower()
        user = await self.user_repo.get_by_username(identifier)

        if not user or not verify_password(password, user.hashed_password):
            raise AuthServiceError("用户名或密码错误", status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            raise AuthServiceError("账号已被停用", status.HTTP_403_FORBIDDEN)

        return user

    async def issue_token_pair(
        self,
        user: User,
        *,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenPair:
        """Generate access/refresh tokens and persist refresh session."""

        now = datetime.now(timezone.utc)
        access_expiry = timedelta(minutes=settings.access_token_expire_minutes)
        refresh_expiry = timedelta(days=settings.refresh_token_expire_days)

        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=access_expiry,
            additional_claims={
                "username": user.username,
                "type": "access",
            },
        )

        refresh_token = secrets.token_urlsafe(48)
        refresh_token_hash = hash_token(refresh_token)

        session_model = UserSession(
            user_id=user.id,
            refresh_token_hash=refresh_token_hash,
            expires_at=now + refresh_expiry,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.session_repo.create(session_model)

        await self.user_repo.update_last_login(user.id, now)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_expiry.total_seconds()),
            refresh_expires_in=int(refresh_expiry.total_seconds()),
            issued_at=now,
            user=user,
        )

    async def refresh_tokens(
        self,
        refresh_token: str,
        *,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenPair:
        """Validate refresh token and rotate tokens."""

        now = datetime.now(timezone.utc)
        token_hash = hash_token(refresh_token)
        session = await self.session_repo.get_active_by_token_hash(token_hash)
        if not session:
            raise AuthServiceError("刷新令牌无效", status.HTTP_401_UNAUTHORIZED)

        if session.expires_at < now:
            await self.session_repo.deactivate(session)
            raise AuthServiceError("刷新令牌已过期", status.HTTP_401_UNAUTHORIZED)

        user = await self.user_repo.get_by_id(session.user_id)
        if not user or not user.is_active:
            await self.session_repo.deactivate(session)
            raise AuthServiceError("账号不可用", status.HTTP_403_FORBIDDEN)

        await self.session_repo.deactivate(session)

        return await self.issue_token_pair(user, user_agent=user_agent, ip_address=ip_address)

    async def logout(self, refresh_token: str) -> None:
        """Explicitly revoke a refresh token."""

        token_hash = hash_token(refresh_token)
        session = await self.session_repo.get_active_by_token_hash(token_hash)
        if session:
            await self.session_repo.deactivate(session)