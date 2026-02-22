"""User SQLAlchemy model and Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    """User table: email is primary key and login identifier."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Optional per-user storage limit (bytes). None = use server limit only.
    storage_limit_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


# Pydantic schemas for API
class UserCreate(BaseModel):
    """Payload for admin creating a new user."""

    email: EmailStr
    first_name: str
    last_name: str


class UserResponse(BaseModel):
    """User as returned by API (no password)."""

    model_config = ConfigDict(from_attributes=True)

    email: str
    first_name: str
    last_name: str
    is_admin: bool
    created_at: datetime
    storage_used_bytes: Optional[int] = None
    storage_limit_bytes: Optional[int] = None


class UserCreateResponse(UserResponse):
    """Response for admin create user. Includes temp_password only when SMTP is not configured (e.g. E2E)."""

    temp_password: Optional[str] = None


class UserLogin(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str


class TokenPair(BaseModel):
    """Access and refresh token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Refresh token request body."""

    refresh_token: str


class ChangePassword(BaseModel):
    """Request body for changing own password."""

    current_password: str
    new_password: str


class UserStorageLimitUpdate(BaseModel):
    """Request body for admin to set a user's storage limit (bytes). None = no per-user limit."""

    storage_limit_bytes: Optional[int] = None
