import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt import create_access_token
from app.files.storage import user_base_path
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


def test_upload_with_leading_slash_and_hash_sync(auth_headers, session_factory):
    import hashlib
    from app.files.hash_store import FileHash
    from sqlalchemy import select

    content = b"content for leading slash test"
    expected_hash = hashlib.sha256(content).hexdigest()

    # 1. Upload file with leading slash
    response = client.post(
        "/api/files/upload?path=/nested/stream_leading.txt",
        content=content,
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "nested/stream_leading.txt"
    assert data["hash"] == expected_hash

    # 2. Verify file listing includes the hash
    list_resp = client.get("/api/files/list", headers=auth_headers)
    assert list_resp.status_code == 200
    files = list_resp.json()
    item = next((f for f in files if f["path"] == "nested/stream_leading.txt"), None)
    assert item is not None
    assert item["hash"] == expected_hash

    # 3. Delete the file
    del_resp = client.delete(
        "/api/files/delete?path=nested/stream_leading.txt",
        headers=auth_headers,
    )
    assert del_resp.status_code == 200

    # 4. Verify no ghost records remain in file_hashes table for this file
    import asyncio
    async def verify_hashes():
        async with session_factory() as session:
            res = await session.execute(
                select(FileHash).where(
                    FileHash.user_email == "test@example.com",
                    FileHash.path.in_(["nested/stream_leading.txt", "/nested/stream_leading.txt"])
                )
            )
            hashes = res.scalars().all()
            assert len(hashes) == 0

    asyncio.run(verify_hashes())


def test_upload_overwrite_smaller_file_clamps_quota(auth_headers, session_factory):
    from app.users.models import User
    from sqlalchemy import select, update
    import asyncio

    # Upload initial 100-byte file
    client.post(
        "/api/files/upload?path=clamp_test.txt",
        content=b"a" * 100,
        headers=auth_headers,
    )

    # Artificially set storage_used_bytes to 10
    async def set_usage():
        async with session_factory() as session:
            await session.execute(
                update(User)
                .where(User.email == "test@example.com")
                .values(storage_used_bytes=10)
            )
            await session.commit()
    asyncio.run(set_usage())

    # Overwrite with 20-byte file (diff is -80)
    response = client.post(
        "/api/files/upload?path=clamp_test.txt",
        content=b"b" * 20,
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Verify storage_used_bytes was clamped to 0 rather than negative (-70)
    async def check_usage():
        async with session_factory() as session:
            res = await session.execute(
                select(User).where(User.email == "test@example.com")
            )
            user = res.scalar_one()
            assert user.storage_used_bytes == 0
    asyncio.run(check_usage())

