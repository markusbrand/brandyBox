"""User routes: login, refresh, me, admin create/delete."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin, get_current_user
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    get_subject_from_refresh,
    verify_password,
)
from app.config import get_settings
from app.db.session import get_db
from app.users.models import (
    RefreshRequest,
    TokenPair,
    User,
    UserCreate,
    UserResponse,
    UserLogin,
)
from app.limiter import limiter
from app.users.service import create_user as do_create_user, get_user_by_email

router = APIRouter(prefix="/api", tags=["users"])


@router.post("/auth/login", response_model=TokenPair)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: UserLogin,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    """Login with email and password; returns access and refresh tokens."""
    user = await get_user_by_email(session, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    settings = get_settings()
    access = create_access_token(user.email)
    refresh = create_refresh_token(user.email)
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/auth/refresh", response_model=TokenPair)
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    """Exchange refresh token for new access and refresh tokens."""
    email = get_subject_from_refresh(body.refresh_token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    settings = get_settings()
    access = create_access_token(user.email)
    new_refresh = create_refresh_token(user.email)
    return TokenPair(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/users/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Return current authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/users", response_model=UserResponse)
async def admin_create_user(
    payload: UserCreate,
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Create a new user (admin only). Password is sent by email."""
    try:
        user, _ = await do_create_user(session, payload, is_admin=False)
        await session.refresh(user)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email could not be sent. Check SMTP configuration.",
        )


@router.get("/users", response_model=list[UserResponse])
async def admin_list_users(
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserResponse]:
    """List all users (admin only)."""
    result = await session.execute(select(User).order_by(User.email))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.delete("/users/{email}")
async def admin_delete_user(
    email: str,
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a user by email (admin only). Does not remove user folder on disk."""
    if email == current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await session.delete(user)
    return None
