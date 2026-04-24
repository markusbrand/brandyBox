"""Client connections and server-side diagnostic events."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ClientConnection(Base):
    """Last-known client version and sync status per user and client type."""

    __tablename__ = "client_connections"
    __table_args__ = (UniqueConstraint("user_email", "client_type", name="uq_client_connections_user_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(String(255), ForeignKey("users.email", ondelete="CASCADE"), nullable=False)
    client_type: Mapped[str] = mapped_column(String(32), nullable=False)
    client_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    backend_version_at_ping: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


class ServerEvent(Base):
    """Append-only diagnostic events (admin-readable)."""

    __tablename__ = "server_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
