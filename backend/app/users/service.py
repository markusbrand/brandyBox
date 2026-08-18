"""User service: create user, send password email."""

import logging
import secrets
from email.message import EmailMessage
from typing import Optional

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import hash_password
from app.config import get_settings
from app.files.quota import get_disk_usage_bytes
from app.files.storage import user_base_path
from app.users.background_image import USER_BACKGROUND_SENTINEL, clear_user_background_image_files
from app.users.models import User, UserCreate, UserPreferences, UserPreferencesPatch

log = logging.getLogger(__name__)


async def send_password_email(
    to_email: str,
    temp_password: str,
    first_name: str,
) -> None:
    """Send the temporary password to the user's email. Raises RuntimeError on failure."""
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from:
        raise RuntimeError("SMTP not configured (BRANDYBOX_SMTP_HOST / SMTP_FROM)")
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = "Your Brandy Box password"
    msg.set_content(f"""Hello {first_name},

Your Brandy Box account has been created. Use this password to log in (you can change it later in settings):

  {temp_password}

Log in at the Brandy Box desktop app with your email and this password.

Best regards,
Brandy Box
""")
    # Port 587 = STARTTLS (connect plain then upgrade). Port 465 = direct TLS.
    use_tls = settings.smtp_port == 465
    start_tls = settings.smtp_port == 587
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=use_tls,
            start_tls=start_tls,
        )
    except Exception as e:
        log.warning("SMTP send failed to %s: %s", to_email, e)
        raise RuntimeError("Email could not be sent. Check SMTP configuration.") from e


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """Return user by email or None."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    payload: UserCreate,
    is_admin: bool = False,
    skip_email: bool = False,
) -> tuple[User, str]:
    """
    Create a new user: store in DB and optionally send temp password by email.
    When skip_email=True (e.g. E2E request with X-E2E-Return-Temp-Password), no email is sent.
    Returns (user, temporary_password). Caller must commit session.
    """
    existing = await get_user_by_email(session, payload.email)
    if existing:
        raise ValueError(f"User already exists: {payload.email}")
    temp_password = secrets.token_urlsafe(12)
    password_hash = hash_password(temp_password)
    user = User(
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password_hash=password_hash,
        is_admin=is_admin,
    )
    session.add(user)
    await session.flush()
    if skip_email:
        log.info("User %s created (E2E/skip_email); temp password returned in response", payload.email)
    else:
        settings = get_settings()
        if settings.smtp_host and settings.smtp_from:
            try:
                await send_password_email(payload.email, temp_password, payload.first_name)
            except RuntimeError:
                raise
            except Exception as e:
                log.warning("Failed to send password email to %s: %s", payload.email, e)
                raise RuntimeError("Email could not be sent. Check SMTP configuration.") from e
        else:
            log.info(
                "User %s created; SMTP not configured. Temporary password: %s",
                payload.email,
                temp_password,
            )
    return user, temp_password


async def ensure_admin_exists(session: AsyncSession) -> None:
    """
    If BRANDYBOX_ADMIN_EMAIL and BRANDYBOX_ADMIN_INITIAL_PASSWORD are set
    and no user exists with that email, create the first admin user.
    """
    settings = get_settings()
    if not settings.admin_email or not settings.admin_initial_password:
        return
    existing = await get_user_by_email(session, settings.admin_email)
    if existing:
        if not existing.is_admin:
            log.info("Promoting existing user %s to admin", settings.admin_email)
            existing.is_admin = True
            await session.commit()
        return
    log.info("Creating bootstrap admin user email=%s", settings.admin_email)
    from app.users.models import UserCreate as UC
    payload = UC(
        email=settings.admin_email,
        first_name="Admin",
        last_name="User",
    )
    user = User(
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password_hash=hash_password(settings.admin_initial_password),
        is_admin=True,
    )
    # Recalculate usage for bootstrap admin
    try:
        base = user_base_path(user.email)
        if base.exists():
            user.storage_used_bytes = get_disk_usage_bytes(base)
    except Exception:
        pass
    session.add(user)


def read_user_preferences(user: User) -> UserPreferences:
    """Parse preferences_json or return defaults."""
    if not user.preferences_json or not str(user.preferences_json).strip():
        return UserPreferences()
    try:
        return UserPreferences.model_validate_json(user.preferences_json)
    except Exception:
        log.warning("Invalid preferences_json for user=%s; resetting view to defaults", user.email)
        return UserPreferences()


async def patch_user_preferences(
    user: User,
    patch: UserPreferencesPatch,
    session: AsyncSession,
) -> UserPreferences:
    """Merge patch into stored JSON.

    Uses ``model_dump(exclude_unset=True)`` so JSON ``null`` for
    ``content_background_image`` clears the field (and uploaded file on disk),
    instead of being treated as "omit this key".
    """
    cur = read_user_preferences(user)
    data = cur.model_dump()
    patch_dict = patch.model_dump(exclude_unset=True)

    if "theme" in patch_dict:
        t = (patch_dict["theme"] or "").strip().lower()
        if t in ("light", "dark", "system"):
            data["theme"] = t
    if "content_background_image" in patch_dict:
        new_val = patch_dict["content_background_image"]
        # Uploaded image lives on disk; clear it when switching to URL, data URL, or off.
        if new_val != USER_BACKGROUND_SENTINEL:
            clear_user_background_image_files(user.email)
        data["content_background_image"] = new_val
    if "content_background_opacity" in patch_dict:
        o = patch_dict["content_background_opacity"]
        data["content_background_opacity"] = max(0.0, min(1.0, float(o)))
    if "favorite_paths" in patch_dict:
        data["favorite_paths"] = list(patch_dict["favorite_paths"])
    merged = UserPreferences.model_validate(data)
    user.preferences_json = merged.model_dump_json()
    await session.flush()
    return merged
