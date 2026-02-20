"""SQLAlchemy model for storing content hashes per user/path."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class FileHash(Base):
    """Content hash (SHA-256) for a file. Used so clients can skip download when hash matches."""

    __tablename__ = "file_hashes"

    user_email: Mapped[str] = mapped_column(String(255), primary_key=True)
    path: Mapped[str] = mapped_column(String(2048), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex
