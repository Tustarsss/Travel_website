"""fastapi-users integration: user manager, adapters, and routers."""

from __future__ import annotations

from typing import AsyncGenerator
from datetime import datetime, UTC
from uuid import UUID

from fastapi import Depends, Request, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers, InvalidPasswordException
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import settings
from .db import get_session_maker
from ..models.users import User


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    maker = get_session_maker()
    async with maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_db_session)) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(BaseUserManager[User, UUID]):
    reset_password_token_secret = settings.jwt_secret_key
    verification_token_secret = settings.jwt_secret_key

    def parse_id(self, user_id: str | UUID) -> UUID:  # type: ignore[override]
        """Convert the user ID from JWT (string) to UUID primary key."""
        if isinstance(user_id, UUID):
            return user_id
        try:
            return UUID(user_id)
        except (TypeError, ValueError) as exc:  # pragma: no cover
            raise ValueError("Invalid user id in token") from exc

    async def validate_password(self, password: str, user: User | None = None) -> None:
        # Basic password policy; can be extended
        if len(password) < 8:
            raise InvalidPasswordException(reason="密码长度至少为 8 位")

    async def on_after_register(self, user: User, request: Request | None = None) -> None:  # noqa: D401
        # Hook for logging or welcome email in the future
        return None

    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response: object | None = None,
    ) -> None:  # noqa: D401
        """Update last_login_at on successful login (best-effort)."""
        try:
            user.last_login_at = datetime.now(UTC)
            await self.user_db.update(user)
        except Exception:  # pragma: no cover - non-critical
            pass

    async def create(self, user_create, safe: bool = False, request: Request | None = None) -> User:
        """Ensure username uniqueness before delegating to the base create logic."""
        # Check username uniqueness
        if getattr(user_create, "username", None):
            result = await self.user_db.session.execute(
                select(User).where(User.username == user_create.username)
            )
            if result.scalar_one_or_none() is not None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

        # Delegate to base manager (handles email uniqueness, password hashing, etc.)
        return await super().create(user_create, safe=safe, request=request)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.jwt_secret_key, lifetime_seconds=settings.access_token_expire_minutes * 60)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


fastapi_users = FastAPIUsers[User, UUID](get_user_manager, [auth_backend])

# Expose dependencies for current user
current_active_user = fastapi_users.current_user(active=True)