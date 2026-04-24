"""OAuth transient storage (SQLite)."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OAuthState(Base):
    """CSRF state for Google OAuth start."""

    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OAuthExchange(Base):
    """One-time token exchange after Google redirect."""

    __tablename__ = "oauth_exchanges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
