"""API tests with TestClient: health, login, me, file list."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient for the FastAPI app. Use as context manager so lifespan runs (init_db, admin bootstrap).
    Override storage path so /me and other routes do not touch /mnt/shared_storage in CI."""
    monkeypatch.setenv("BRANDYBOX_STORAGE_BASE_PATH", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    """GET /health returns 200 and status ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_login_success(client: TestClient) -> None:
    """POST /api/auth/login with bootstrap admin returns tokens."""
    r = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data.get("token_type") == "bearer"
    assert data.get("expires_in") > 0


def test_login_invalid_password(client: TestClient) -> None:
    """POST /api/auth/login with wrong password returns 401."""
    r = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert r.status_code == 401
    assert "Invalid" in (r.json().get("detail") or "")


def test_login_nonexistent_user(client: TestClient) -> None:
    """POST /api/auth/login with unknown email returns 401."""
    r = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "any"},
    )
    assert r.status_code == 401


def test_me_requires_auth(client: TestClient) -> None:
    """GET /api/users/me without Bearer returns 401."""
    r = client.get("/api/users/me")
    assert r.status_code == 401

def test_me_with_token(client: TestClient) -> None:
    """GET /api/users/me with valid token returns user."""
    login_r = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    assert login_r.status_code == 200
    token = login_r.json()["access_token"]
    r = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "test@example.com"
    assert data["is_admin"] is True
    assert "password" not in data
