import pytest
import uuid
import os
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
                is_admin=True,
                storage_used_bytes=0
            )
            session.add(user)
            await session.commit()

    # Ensure user folder exists
    user_dir = user_base_path("test@example.com")
    user_dir.mkdir(parents=True, exist_ok=True)

    yield storage_base
    shutil.rmtree(storage_base)

def test_chunked_upload_success(auth_headers):
    path = "chunked.txt"
    # 1. Init
    response = client.post(f"/api/files/upload/init?path={path}", headers=auth_headers)
    assert response.status_code == 200
    upload_id = response.json()["upload_id"]

    # 2. Upload chunks
    chunk1 = b"hello "
    chunk2 = b"world"

    response = client.post(f"/api/files/upload/chunk?upload_id={upload_id}&index=0", content=chunk1, headers=auth_headers)
    assert response.status_code == 200

    response = client.post(f"/api/files/upload/chunk?upload_id={upload_id}&index=1", content=chunk2, headers=auth_headers)
    assert response.status_code == 200

    # 3. Finalize
    response = client.post(f"/api/files/upload/finalize?upload_id={upload_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["path"] == path
    assert response.json()["size"] == len(chunk1) + len(chunk2)

    # Verify file
    target = user_base_path("test@example.com") / path
    assert target.exists()
    assert target.read_bytes() == chunk1 + chunk2

def test_chunked_upload_invalid_id(auth_headers):
    response = client.post("/api/files/upload/chunk?upload_id=invalid&index=0", content=b"data", headers=auth_headers)
    assert response.status_code == 404

def test_chunked_upload_finalize_not_found(auth_headers):
    response = client.post("/api/files/upload/finalize?upload_id=nonexistent", headers=auth_headers)
    assert response.status_code == 404

def test_chunked_upload_large_number_of_chunks(auth_headers):
    path = "large_chunked.txt"
    response = client.post(f"/api/files/upload/init?path={path}", headers=auth_headers)
    upload_id = response.json()["upload_id"]

    num_chunks = 20
    chunk_data = b"chunk content "
    for i in range(num_chunks):
        response = client.post(f"/api/files/upload/chunk?upload_id={upload_id}&index={i}", content=chunk_data, headers=auth_headers)
        assert response.status_code == 200

    response = client.post(f"/api/files/upload/finalize?upload_id={upload_id}", headers=auth_headers)
    assert response.status_code == 200

    target = user_base_path("test@example.com") / path
    assert target.exists()
    assert target.read_bytes() == chunk_data * num_chunks
