"""JWT creation and validation."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bcrypt limits input to 72 bytes; truncate to avoid ValueError
_BCRYPT_MAX_BYTES = 72


def _truncate_for_bcrypt(s: str) -> str:
    """Truncate string to 72 bytes (UTF-8) for bcrypt."""
    b = s.encode("utf-8")[: _BCRYPT_MAX_BYTES]
    return b.decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    """Hash a password for storage. Passwords longer than 72 bytes are truncated."""
    return pwd_context.hash(_truncate_for_bcrypt(password))


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a hash."""
    return pwd_context.verify(_truncate_for_bcrypt(plain), hashed)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived access JWT. Subject is user email."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


def create_refresh_token(subject: str) -> str:
    """Create a refresh JWT for obtaining new access tokens."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT; return payload or None."""
    settings = get_settings()
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None


def get_subject_from_access(token: str) -> Optional[str]:
    """Return subject (email) if token is a valid access token."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload.get("sub")


def get_subject_from_refresh(token: str) -> Optional[str]:
    """Return subject (email) if token is a valid refresh token."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    return payload.get("sub")
