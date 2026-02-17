"""User SQLAlchemy model and Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr
from sqlalchemy import Boolean, DateTime, String, Text, func
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


# Pydantic schemas for API
class UserCreate(BaseModel):
    """Payload for admin creating a new user."""

    email: EmailStr
    first_name: str
    last_name: str


class UserResponse(BaseModel):
    """User as returned by API (no password)."""

    email: str
    first_name: str
    last_name: str
    is_admin: bool
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


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
