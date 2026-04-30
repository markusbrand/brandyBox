"""HTTP-level security tests for file routes: traversal, body cap, user isolation."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.files.storage import user_base_path


@pytest.fixture
def client(tmp_path, monkeypatch):
    """App with isolated storage under tmp_path."""
    monkeypatch.setenv("BRANDYBOX_STORAGE_BASE_PATH", str(tmp_path))
    with TestClient(app) as c:
        yield c


def _bearer(client: TestClient) -> dict[str, str]:
    r = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.parametrize(
    "bad_path",
    [
        "../../etc/passwd",
        "sub/../../../etc/passwd",
        "sub/..",
    ],
)
def test_upload_rejects_path_traversal(client: TestClient, bad_path: str) -> None:
    """Unsafe path segments return 400 (never write outside user root)."""
    r = client.post(
        f"/api/files/upload?path={bad_path}",
        content=b"x",
        headers=_bearer(client),
    )
    assert r.status_code == 400, (bad_path, r.text)


def test_download_rejects_traversal(client: TestClient) -> None:
    r = client.get(
        "/api/files/download?path=../other",
        headers=_bearer(client),
    )
    assert r.status_code == 400


def test_delete_rejects_traversal(client: TestClient) -> None:
    r = client.delete(
        "/api/files/delete?path=foo/../../bar",
        headers=_bearer(client),
    )
    assert r.status_code == 400


def test_upload_rejects_missing_path(client: TestClient) -> None:
    r = client.post("/api/files/upload", content=b"hi", headers=_bearer(client))
    assert r.status_code == 400


def test_max_single_upload_bytes_returns_413(client: TestClient, monkeypatch) -> None:
    """When BRANDYBOX_MAX_SINGLE_UPLOAD_BYTES is set, oversized body gets 413."""
    monkeypatch.setenv("BRANDYBOX_MAX_SINGLE_UPLOAD_BYTES", "100")
    r = client.post(
        "/api/files/upload?path=capped.bin",
        content=b"x" * 200,
        headers=_bearer(client),
    )
    assert r.status_code == 413
    assert "maximum" in r.json().get("detail", "").lower() or "exceeds" in r.json().get("detail", "").lower()
    target = user_base_path("test@example.com") / "capped.bin"
    assert not target.exists()


def test_user_cannot_download_other_users_file(client: TestClient) -> None:
    """JWT scope: another user's object name in own tree is 404, not cross-tenant leak."""
    admin = _bearer(client)
    cr = client.post(
        "/api/users",
        json={
            "email": "peer@example.com",
            "first_name": "Peer",
            "last_name": "User",
        },
        headers=admin,
    )
    assert cr.status_code == 200, cr.text
    peer_pw = cr.json().get("temp_password")
    assert peer_pw, "expected temp_password when SMTP unset"

    pr = client.post(
        "/api/auth/login",
        json={"email": "peer@example.com", "password": peer_pw},
    )
    assert pr.status_code == 200
    peer_headers = {"Authorization": f"Bearer {pr.json()['access_token']}"}

    up = client.post(
        "/api/files/upload?path=private/secret.bin",
        content=b"peer-secret",
        headers=peer_headers,
    )
    assert up.status_code == 200

    # Admin (test@example.com) must not download path that only exists under peer
    dl = client.get(
        "/api/files/download?path=private/secret.bin",
        headers=admin,
    )
    assert dl.status_code == 404


# --- /api/files/folders -----------------------------------------------------


def test_list_folders_empty(client: TestClient) -> None:
    """A fresh user has no folders."""
    r = client.get("/api/files/folders", headers=_bearer(client))
    assert r.status_code == 200
    assert r.json() == []


def test_list_folders_after_upload(client: TestClient) -> None:
    """Uploading a/b/c.txt creates folders 'a' and 'a/b' visible via /folders."""
    headers = _bearer(client)
    up = client.post(
        "/api/files/upload?path=a/b/c.txt",
        content=b"hi",
        headers=headers,
    )
    assert up.status_code == 200, up.text

    r = client.get("/api/files/folders", headers=headers)
    assert r.status_code == 200, r.text
    paths = {row["path"] for row in r.json()}
    assert paths == {"a", "a/b"}


def test_list_files_returns_size(client: TestClient) -> None:
    """API 0.3.0: each file row in /list includes a 'size' field in bytes."""
    headers = _bearer(client)
    body = b"x" * 17
    up = client.post(
        "/api/files/upload?path=sized.bin",
        content=body,
        headers=headers,
    )
    assert up.status_code == 200, up.text

    r = client.get("/api/files/list", headers=headers)
    assert r.status_code == 200
    rows = {row["path"]: row for row in r.json()}
    assert "sized.bin" in rows
    assert rows["sized.bin"]["size"] == len(body)


# --- /api/files/mkdir -------------------------------------------------------


def test_mkdir_creates_empty_folder(client: TestClient) -> None:
    """POST /api/files/mkdir creates an empty folder visible via /folders."""
    headers = _bearer(client)
    r = client.post("/api/files/mkdir?path=Photos/2024", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["path"] == "Photos/2024"
    assert body["created"] is True

    folders = client.get("/api/files/folders", headers=headers).json()
    paths = {row["path"] for row in folders}
    assert "Photos" in paths
    assert "Photos/2024" in paths


def test_mkdir_idempotent(client: TestClient) -> None:
    """Calling mkdir twice returns created=False the second time."""
    headers = _bearer(client)
    first = client.post("/api/files/mkdir?path=Same", headers=headers)
    assert first.status_code == 200
    assert first.json()["created"] is True
    second = client.post("/api/files/mkdir?path=Same", headers=headers)
    assert second.status_code == 200
    assert second.json()["created"] is False


def test_mkdir_conflict_with_file(client: TestClient) -> None:
    """If a file already lives at the path, mkdir returns 409."""
    headers = _bearer(client)
    up = client.post(
        "/api/files/upload?path=blocker.txt",
        content=b"f",
        headers=headers,
    )
    assert up.status_code == 200
    r = client.post("/api/files/mkdir?path=blocker.txt", headers=headers)
    assert r.status_code == 409


def test_mkdir_rejects_traversal(client: TestClient) -> None:
    """mkdir rejects unsafe path segments with 400."""
    headers = _bearer(client)
    r = client.post("/api/files/mkdir?path=../etc", headers=headers)
    assert r.status_code == 400


def test_mkdir_requires_path(client: TestClient) -> None:
    """Missing 'path' query param returns 400."""
    headers = _bearer(client)
    r = client.post("/api/files/mkdir", headers=headers)
    assert r.status_code == 400
