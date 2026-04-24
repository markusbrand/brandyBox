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
