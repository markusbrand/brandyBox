"""User routes: login, refresh, me, admin create/delete."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin, get_current_user
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    get_subject_from_refresh,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.db.session import get_db
from app.files.quota import (
    get_server_storage_limit_bytes,
    get_user_storage_limit_bytes,
    get_user_used_bytes,
)
from app.users.models import (
    ChangePassword,
    RefreshRequest,
    TokenPair,
    User,
    UserCreate,
    UserCreateResponse,
    UserLogin,
    UserPreferences,
    UserPreferencesPatch,
    UserResponse,
    UserStorageLimitUpdate,
)
from app.limiter import limiter
from app.users.background_image import (
    USER_BACKGROUND_SENTINEL,
    clear_user_background_image_files,
    find_stored_background_path,
    save_user_background_image_bytes,
)
from app.users.service import (
    create_user as do_create_user,
    get_user_by_email,
    patch_user_preferences,
    read_user_preferences,
)

router = APIRouter(prefix="/api", tags=["users"])
log = logging.getLogger(__name__)


@router.post("/auth/login", response_model=TokenPair)
@limiter.limit("60/minute")  # E2E polls login frequently; 60/min avoids 429 on sync scenarios
async def login(
    request: Request,
    body: UserLogin,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    """Login with email and password; returns access and refresh tokens."""
    user = await get_user_by_email(session, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        log.warning("Login failed for email=%s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    log.info("Login successful for email=%s", user.email)
    settings = get_settings()
    access = create_access_token(user.email)
    refresh = create_refresh_token(user.email)
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/auth/refresh", response_model=TokenPair)
@limiter.limit("60/minute")  # Align with login; E2E + normal use
async def refresh(
    request: Request,
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    """Exchange refresh token for new access and refresh tokens."""
    email = get_subject_from_refresh(body.refresh_token)
    if not email:
        log.warning("Refresh failed: invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    user = await get_user_by_email(session, email)
    if not user:
        log.warning("Refresh failed: user not found email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    log.info("Refresh successful for email=%s", user.email)
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
    """Return current authenticated user with storage used/limit."""
    data = UserResponse.model_validate(current_user).model_dump()
    data["storage_used_bytes"] = get_user_used_bytes(current_user.email)
    server_limit = get_server_storage_limit_bytes()
    data["storage_limit_bytes"] = get_user_storage_limit_bytes(
        server_limit, current_user.storage_limit_bytes
    )
    return UserResponse(**data)


@router.get("/users/me/preferences", response_model=UserPreferences)
async def get_my_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPreferences:
    """Return persisted appearance and favorites for the current user."""
    return read_user_preferences(current_user)


@router.patch("/users/me/preferences", response_model=UserPreferences)
async def patch_my_preferences(
    payload: UserPreferencesPatch,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferences:
    """Update appearance and favorites (partial)."""
    return await patch_user_preferences(current_user, payload, session)


@router.get("/users/me/background-image")
@limiter.limit("120/minute")
async def get_my_background_image(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Stream the image uploaded for the web full-page background (Bearer auth required)."""
    found = find_stored_background_path(current_user.email)
    if not found:
        log.warning("get_my_background_image: no file for user=%s", current_user.email)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No background image uploaded",
        )
    path, media_type = found
    log.info("get_my_background_image user=%s path=%s", current_user.email, path.name)
    return FileResponse(path=path, media_type=media_type)


@router.post("/users/me/background-image", response_model=UserPreferences)
@limiter.limit("30/minute")
async def upload_my_background_image(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferences:
    """
    Upload a full-page background image (JPEG, PNG, GIF, or WebP), max 5 MB raw body.

    Stores the file under the user's ``.brandybox/`` folder and sets
    ``content_background_image`` to ``bb:server-background`` so the web client
    can load it with Bearer auth via this route and use a blob URL in CSS.
    """
    body = await request.body()
    try:
        save_user_background_image_bytes(current_user.email, body)
    except ValueError as e:
        log.warning("upload_my_background_image rejected user=%s: %s", current_user.email, e)
        msg = str(e)
        if "too large" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    merged = await patch_user_preferences(
        current_user,
        UserPreferencesPatch(content_background_image=USER_BACKGROUND_SENTINEL),
        session,
    )
    log.info("upload_my_background_image user=%s ok", current_user.email)
    return merged


@router.delete("/users/me/background-image", response_model=UserPreferences)
@limiter.limit("30/minute")
async def delete_my_background_image(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferences:
    """Remove the uploaded background file and clear ``content_background_image``."""
    clear_user_background_image_files(current_user.email)
    merged = await patch_user_preferences(
        current_user,
        UserPreferencesPatch(content_background_image=None),
        session,
    )
    log.info("delete_my_background_image user=%s", current_user.email)
    return merged


@router.post("/auth/change-password")
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    body: ChangePassword,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Change the current user's password. Requires current password."""
    if not verify_password(body.current_password, current_user.password_hash):
        log.warning("Change password failed for email=%s: wrong current password", current_user.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    if not body.new_password or len(body.new_password.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )
    current_user.password_hash = hash_password(body.new_password)
    await session.commit()
    log.info("Password changed for email=%s", current_user.email)
    return {"detail": "Password updated"}


# Header sent by E2E runner so backend returns temp_password and skips sending email (SMTP not required).
E2E_RETURN_TEMP_PASSWORD_HEADER = "X-E2E-Return-Temp-Password"


@router.post("/users", response_model=UserCreateResponse)
async def admin_create_user(
    request: Request,
    payload: UserCreate,
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserCreateResponse:
    """Create a new user (admin only). Password is sent by email, or returned when E2E header is set or SMTP not configured."""
    e2e_return_password = (request.headers.get(E2E_RETURN_TEMP_PASSWORD_HEADER) or "").strip().lower() in ("true", "1")
    try:
        user, temp_password = await do_create_user(
            session, payload, is_admin=False, skip_email=e2e_return_password
        )
        await session.refresh(user)
        log.info("Admin %s created user email=%s", current_user.email, user.email)
        data = UserResponse.model_validate(user).model_dump()
        # Return temp_password when E2E requested it, or when SMTP is not configured
        if e2e_return_password or not get_settings().smtp_host or not get_settings().smtp_from:
            data["temp_password"] = temp_password
        return UserCreateResponse(**data)
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
    """List all users (admin only) with storage used/limit per user."""
    result = await session.execute(select(User).order_by(User.email))
    users = result.scalars().all()
    log.info("Admin %s listed users count=%d", current_user.email, len(users))
    server_limit = get_server_storage_limit_bytes()
    out = []
    for u in users:
        data = UserResponse.model_validate(u).model_dump()
        data["storage_used_bytes"] = get_user_used_bytes(u.email)
        data["storage_limit_bytes"] = get_user_storage_limit_bytes(
            server_limit, u.storage_limit_bytes
        )
        out.append(UserResponse(**data))
    return out


@router.patch("/users/{email}", response_model=UserResponse)
async def admin_update_user_storage_limit(
    email: str,
    payload: UserStorageLimitUpdate,
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Update a user's storage limit (admin only). storage_limit_bytes: max bytes or null for server default."""
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.storage_limit_bytes is not None and payload.storage_limit_bytes < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="storage_limit_bytes must be non-negative",
        )
    user.storage_limit_bytes = payload.storage_limit_bytes
    await session.commit()
    await session.refresh(user)
    log.info("Admin %s set storage_limit for %s to %s", current_user.email, email, payload.storage_limit_bytes)
    data = UserResponse.model_validate(user).model_dump()
    data["storage_used_bytes"] = get_user_used_bytes(user.email)
    data["storage_limit_bytes"] = get_user_storage_limit_bytes(
        get_server_storage_limit_bytes(), user.storage_limit_bytes
    )
    return UserResponse(**data)


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
    log.info("Admin %s deleted user email=%s", current_user.email, email)
    await session.delete(user)
    return None
