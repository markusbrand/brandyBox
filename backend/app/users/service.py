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
from app.users.models import User, UserCreate

log = logging.getLogger(__name__)


async def send_password_email(
    to_email: str,
    temp_password: str,
    first_name: str,
) -> None:
    """Send the temporary password to the user's email. Raises on SMTP failure."""
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
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        use_tls=settings.smtp_port == 587,
    )


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """Return user by email or None."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    payload: UserCreate,
    is_admin: bool = False,
) -> tuple[User, str]:
    """
    Create a new user: store in DB and send temp password by email.
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
    try:
        await send_password_email(payload.email, temp_password, payload.first_name)
    except Exception as e:
        log.warning("Failed to send password email to %s: %s", payload.email, e)
        raise
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
    session.add(user)
