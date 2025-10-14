"""Authentication endpoints for user management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api import deps
from app.models.users import User
from app.schemas.auth import LoginRequest, TokenPair, RefreshRequest, LogoutRequest
from app.schemas.user import UserCreateRequest, UserPublic
from app.services.auth import AuthService, AuthServiceError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreateRequest,
    service: AuthService = Depends(deps.get_auth_service),
) -> UserPublic:
    """Register a new user account."""

    try:
        user = await service.register_user(payload)
    except AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return UserPublic.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    request: Request,
    service: AuthService = Depends(deps.get_auth_service),
) -> TokenPair:
    """Authenticate with username and password."""

    try:
        user = await service.authenticate_user(payload.identifier, payload.password)
        tokens = await service.issue_token_pair(
            user,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    payload: RefreshRequest,
    request: Request,
    service: AuthService = Depends(deps.get_auth_service),
) -> TokenPair:
    """Refresh access and refresh tokens."""

    try:
        tokens = await service.refresh_tokens(
            payload.refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    service: AuthService = Depends(deps.get_auth_service),
) -> None:
    """Invalidate a refresh token."""

    await service.logout(payload.refresh_token)


@router.get("/me", response_model=UserPublic)
async def get_current_user_profile(
    current_user: User = Depends(deps.get_current_user),
) -> UserPublic:
    """Return the authenticated user's profile."""

    return UserPublic.model_validate(current_user)
