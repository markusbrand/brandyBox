import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt import create_access_token
from app.files.storage import user_base_path
import os
import shutil

client = TestClient(app)

@pytest.fixture
def auth_headers():
    token = create_access_token("test@example.com")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
async def setup_storage(tmp_path, monkeypatch, init_test_db, session_factory):
    storage_base = tmp_path / "storage"
    storage_base.mkdir()
    monkeypatch.setenv("BRANDYBOX_STORAGE_BASE_PATH", str(storage_base))
    from app.config import get_settings
    monkeypatch.setattr("app.files.routes.get_settings", lambda: get_settings())

    # Ensure user exists in DB
    from app.users.models import User
    from app.auth.jwt import hash_password
    from sqlalchemy import select
    async with session_factory() as session:
        res = await session.execute(select(User).where(User.email == "test@example.com"))
        if not res.scalar_one_or_none():
            user = User(
                email="test@example.com",
                first_name="Test",
                last_name="User",
                password_hash=hash_password("testpass123"),
                is_admin=True
            )
            session.add(user)
            await session.commit()

    # Ensure user folder exists
    user_dir = user_base_path("test@example.com")
    user_dir.mkdir(parents=True, exist_ok=True)

    yield storage_base
    shutil.rmtree(storage_base)

def test_upload_streaming_success(auth_headers):
    content = b"streaming content" * 100
    response = client.post(
        "/api/files/upload?path=stream.txt",
        content=content,
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["size"] == len(content)

    # Verify file on disk
    target = user_base_path("test@example.com") / "stream.txt"
    assert target.exists()
    assert target.read_bytes() == content

def test_upload_streaming_quota_exceeded(auth_headers, monkeypatch):
    # Set a very small limit
    monkeypatch.setenv("BRANDYBOX_STORAGE_LIMIT", "100MB")

    # Mock user quota to be very small
    from app.users.models import User
    from sqlalchemy import update
    async def set_limit():
        from app.db.session import get_session
        async with get_session() as session:
            await session.execute(
                update(User)
                .where(User.email == "test@example.com")
                .values(storage_limit_bytes=50)
            )
            await session.commit()

    import asyncio
    asyncio.run(set_limit())

    content = b"a" * 101
    response = client.post(
        "/api/files/upload?path=too_large.txt",
        content=content,
        headers=auth_headers
    )
    assert response.status_code == 507
    assert "reached" in response.json()["detail"].lower()

    # Verify file not on disk
    target = user_base_path("test@example.com") / "too_large.txt"
    assert not target.exists()

def test_upload_streaming_large_file(auth_headers):
    # Ensure user has large enough limit
    from app.users.models import User
    from sqlalchemy import update
    async def set_limit():
        from app.db.session import get_session
        async with get_session() as session:
            await session.execute(
                update(User)
                .where(User.email == "test@example.com")
                .values(storage_limit_bytes=10*1024*1024)
            )
            await session.commit()
    import asyncio
    asyncio.run(set_limit())

    # Test with 1MB file (not huge but enough to test streaming logic)
    content = b"large" * 200000
    response = client.post(
        "/api/files/upload?path=large.txt",
        content=content,
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["size"] == len(content)

    target = user_base_path("test@example.com") / "large.txt"
    assert target.exists()
    assert target.stat().st_size == len(content)
