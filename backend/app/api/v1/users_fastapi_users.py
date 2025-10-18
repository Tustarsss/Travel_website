"""Routers powered by fastapi-users."""

from fastapi import APIRouter, Depends

from ...core.auth import auth_backend, fastapi_users, current_active_user
from ...models.users import User
from ...schemas.auth_users import UserCreate, UserRead, UserUpdate


router = APIRouter()

# Login via JWT (bearer). Returns {access_token, token_type}
router.include_router(
	fastapi_users.get_auth_router(auth_backend),
	prefix="/auth/jwt",
	tags=["auth"],
)

# Registration with custom schemas (email+username+password)
router.include_router(
	fastapi_users.get_register_router(UserRead, UserCreate),
	prefix="/auth",
	tags=["auth"],
)

# Reset password / Verify email (optional endpoints)
router.include_router(
	fastapi_users.get_reset_password_router(),
	prefix="/auth",
	tags=["auth"],
)
router.include_router(
	fastapi_users.get_verify_router(UserRead),
	prefix="/auth",
	tags=["auth"],
)

# Users management endpoints
router.include_router(
	fastapi_users.get_users_router(UserRead, UserUpdate),
	prefix="/users",
	tags=["users"],
)


@router.get("/auth/me", response_model=UserRead, tags=["auth"])
async def read_me(user: User = Depends(current_active_user)) -> User:
	return user
