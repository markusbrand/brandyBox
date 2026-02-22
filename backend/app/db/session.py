"""SQLite session and engine."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import get_settings

Base = declarative_base()

_settings = get_settings()
# SQLAlchemy async needs sqlite+aiosqlite and path as URL
_db_url = f"sqlite+aiosqlite:///{_settings.db_path}"
_engine = create_async_engine(_db_url, echo=False)
_async_session = async_sessionmaker(
    _engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


def _add_storage_limit_column_if_missing(conn) -> None:
    """Add users.storage_limit_bytes if the column does not exist (migration)."""
    cursor = conn.execute(text("PRAGMA table_info(users)"))
    rows = cursor.fetchall()
    # SQLite returns (cid, name, type, notnull, dflt_value, pk)
    if any(row[1] == "storage_limit_bytes" for row in rows):
        return
    conn.execute(text("ALTER TABLE users ADD COLUMN storage_limit_bytes INTEGER"))


async def init_db() -> None:
    """Create tables if they do not exist, then run migrations."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_storage_limit_column_if_missing)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session (context manager)."""
    async with _async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session."""
    async with get_session() as session:
        yield session
