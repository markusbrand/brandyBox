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
    response = client.post("/api/files/upload/chunk?upload_id=00000000-0000-0000-0000-000000000000&index=0", content=b"data", headers=auth_headers)
    assert response.status_code == 404

def test_chunked_upload_finalize_not_found(auth_headers):
    response = client.post("/api/files/upload/finalize?upload_id=00000000-0000-0000-0000-000000000000", headers=auth_headers)
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

def test_chunked_upload_invalid_uuid(auth_headers):
    response = client.post("/api/files/upload/chunk?upload_id=invalid&index=0", content=b"data", headers=auth_headers)
    assert response.status_code == 422


def test_chunked_upload_directory_not_leaked_in_listings(auth_headers):
    """While chunks are present, neither .uploads nor its chunks appear in list or folders."""
    path = "secret_in_progress.txt"
    res = client.post(f"/api/files/upload/init?path={path}", headers=auth_headers)
    assert res.status_code == 200
    upload_id = res.json()["upload_id"]

    res = client.post(f"/api/files/upload/chunk?upload_id={upload_id}&index=0", content=b"chunk0", headers=auth_headers)
    assert res.status_code == 200

    # Ensure list endpoints do not leak .uploads
    files = client.get("/api/files/list", headers=auth_headers).json()
    folders = client.get("/api/files/folders", headers=auth_headers).json()

    for f in files:
        assert not f["path"].startswith(".uploads")
    for f in folders:
        assert not f["path"].startswith(".uploads")

    # Direct download or delete into .uploads is blocked
    dl = client.get(f"/api/files/download?path=.uploads/{upload_id}/.path", headers=auth_headers)
    assert dl.status_code == 400

    # Finalize cleans up
    client.post(f"/api/files/upload/finalize?upload_id={upload_id}", headers=auth_headers)


@pytest.mark.anyio
async def test_user_with_plus_email_file_operations(session_factory, monkeypatch):
    """Users with + in email can list files, upload, and get storage."""
    from app.users.models import User
    from app.auth.jwt import hash_password

    plus_email = "user+tag@example.com"
    async with session_factory() as session:
        user = User(
            email=plus_email,
            first_name="Plus",
            last_name="User",
            password_hash=hash_password("testpass123"),
            is_admin=False,
            storage_used_bytes=0,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(plus_email)
    headers = {"Authorization": f"Bearer {token}"}

    # User directory creation via list
    res_list = client.get("/api/files/list", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json() == []

    # Upload
    res_upload = client.post("/api/files/upload?path=test_plus.txt", content=b"hello plus", headers=headers)
    assert res_upload.status_code == 200
    assert res_upload.json()["path"] == "test_plus.txt"

    # List again
    res_list2 = client.get("/api/files/list", headers=headers)
    assert res_list2.status_code == 200
    assert len(res_list2.json()) == 1
    assert res_list2.json()[0]["path"] == "test_plus.txt"


def test_upload_over_existing_directory_returns_409(auth_headers):
    # 1. Create directory
    res_mkdir = client.post("/api/files/mkdir?path=docs", headers=auth_headers)
    assert res_mkdir.status_code == 200

    # 2. Attempt single upload over existing directory
    res_upload = client.post("/api/files/upload?path=docs", content=b"data", headers=auth_headers)
    assert res_upload.status_code == 409
    assert "directory already exists" in res_upload.json()["detail"].lower()

    # 3. Attempt upload/init over existing directory
    res_init = client.post("/api/files/upload/init?path=docs", headers=auth_headers)
    assert res_init.status_code == 409
    assert "directory already exists" in res_init.json()["detail"].lower()


def test_chunked_upload_non_contiguous_chunks_fails_400(auth_headers):
    # 1. Init
    res_init = client.post("/api/files/upload/init?path=sparse.txt", headers=auth_headers)
    assert res_init.status_code == 200
    upload_id = res_init.json()["upload_id"]

    # 2. Upload chunk 0 and chunk 2 (chunk 1 missing)
    c0 = client.post(f"/api/files/upload/chunk?upload_id={upload_id}&index=0", content=b"aaa", headers=auth_headers)
    assert c0.status_code == 200
    c2 = client.post(f"/api/files/upload/chunk?upload_id={upload_id}&index=2", content=b"ccc", headers=auth_headers)
    assert c2.status_code == 200

    # 3. Finalize should fail with 400 Bad Request
    res_final = client.post(f"/api/files/upload/finalize?upload_id={upload_id}", headers=auth_headers)
    assert res_final.status_code == 400
    assert "missing chunk index 1" in res_final.json()["detail"].lower()

    # 4. Upload directory should be cleaned up
    user_base = user_base_path("test@example.com")
    upload_dir = user_base / ".uploads" / upload_id
    assert not upload_dir.exists()

