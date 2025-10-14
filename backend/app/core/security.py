"""Security helpers for password hashing and JWT token management."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import status
from passlib.context import CryptContext

from .config import settings


pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using the active CryptContext scheme."""

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""

    return pwd_context.verify(plain_password, hashed_password)


def hash_token(token: str) -> str:
    """Return a deterministic SHA-256 hash for storing refresh tokens."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class TokenValidationResult:
    """Decoded token payload with metadata."""

    subject: str
    payload: Dict[str, Any]
    issued_at: datetime
    expires_at: datetime


class TokenValidationError(Exception):
    """Raised when token validation fails."""

    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def create_access_token(
    *,
    subject: str,
    expires_delta: timedelta,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT access token."""

    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if additional_claims:
        payload.update(additional_claims)

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str, *, expected_type: Optional[str] = None) -> TokenValidationResult:
    """Decode and validate a JWT token."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenValidationError("令牌已过期") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenValidationError("令牌无效") from exc

    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise TokenValidationError("令牌类型错误")

    subject = payload.get("sub")
    if subject is None:
        raise TokenValidationError("令牌缺少主体")

    issued_at = datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc)
    expires_at = datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)

    return TokenValidationResult(subject=str(subject), payload=payload, issued_at=issued_at, expires_at=expires_at)