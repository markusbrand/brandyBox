"""Content-hash storage for fast sync comparison. Hash is SHA-256 of file body."""

import hashlib
import logging
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.files.hash_model import FileHash

log = logging.getLogger(__name__)


async def get_hashes_for_paths(session: AsyncSession, user_email: str, paths: List[str]) -> Dict[str, str]:
    """Return dict path -> content_hash for paths that have a stored hash. Missing paths are omitted."""
    out: Dict[str, str] = {}
    chunk = 500  # stay under SQLite parameter limit
    for i in range(0, len(paths), chunk):
        part = paths[i : i + chunk]
        if not part:
            continue
        result = await session.execute(
            select(FileHash.path, FileHash.content_hash).where(
                FileHash.user_email == user_email,
                FileHash.path.in_(part),
            )
        )
        for row in result.all():
            out[row[0]] = row[1]
    return out


async def set_hash(session: AsyncSession, user_email: str, path: str, content_hash: str) -> None:
    """Store or update content hash for a file. Caller must commit."""
    row = await session.get(FileHash, (user_email, path))
    if row:
        row.content_hash = content_hash
    else:
        session.add(FileHash(user_email=user_email, path=path, content_hash=content_hash))


async def delete_hash(session: AsyncSession, user_email: str, path: str) -> None:
    """Remove stored hash when file is deleted. Caller must commit."""
    row = await session.get(FileHash, (user_email, path))
    if row:
        await session.delete(row)


def compute_hash(body: bytes) -> str:
    """SHA-256 hex digest of file body."""
    return hashlib.sha256(body).hexdigest()
