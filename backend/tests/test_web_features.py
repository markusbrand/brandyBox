"""Web-related API: preferences, meta version, client ping, OAuth exchange."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.oauth.models import OAuthExchange
from app.auth.jwt import create_access_token, create_refresh_token


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with isolated storage path (same pattern as test_api)."""
    monkeypatch.setenv("BRANDYBOX_STORAGE_BASE_PATH", str(tmp_path))
    with TestClient(app) as c:
        yield c


def _auth_headers(client: TestClient, email: str = "test@example.com", password: str = "testpass123") -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_meta_version(client: TestClient) -> None:
    r = client.get("/api/meta/version")
    assert r.status_code == 200
    j = r.json()
    assert "api_version" in j
    assert "min_supported_client_version" in j


def test_preferences_roundtrip(client: TestClient) -> None:
    h = _auth_headers(client)
    r = client.get("/api/users/me/preferences", headers=h)
    assert r.status_code == 200
    assert r.json()["theme"] == "system"
    r2 = client.patch(
        "/api/users/me/preferences",
        headers=h,
        json={"theme": "dark", "favorite_paths": ["a/b.txt"], "content_background_opacity": 0.5},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["theme"] == "dark"
    assert r2.json()["favorite_paths"] == ["a/b.txt"]
    assert r2.json()["content_background_opacity"] == 0.5


def test_client_ping(client: TestClient) -> None:
    h = _auth_headers(client)
    r = client.post(
        "/api/clients/ping",
        headers=h,
        json={"client_type": "tauri", "client_version": "1.0.0-test", "last_sync_ok": True},
    )
    assert r.status_code == 204, r.text


def test_oauth_complete_invalid(client: TestClient) -> None:
    r = client.post("/api/auth/oauth/complete", json={"exchange": str(uuid.uuid4())})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_oauth_complete_success(client: TestClient, session_factory) -> None:
    from app.users.service import get_user_by_email

    ex_id = str(uuid.uuid4())
    async with session_factory() as session:
        user = await get_user_by_email(session, "test@example.com")
        assert user is not None
        session.add(
            OAuthExchange(
                id=ex_id,
                access_token=create_access_token(user.email),
                refresh_token=create_refresh_token(user.email),
            )
        )
    r = client.post("/api/auth/oauth/complete", json={"exchange": ex_id})
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_admin_clients_and_events(client: TestClient) -> None:
    h = _auth_headers(client)
    client.post(
        "/api/clients/ping",
        headers=h,
        json={"client_type": "web", "client_version": "0.1.0"},
    )
    r = client.get("/api/admin/clients", headers=h)
    assert r.status_code == 200, r.text
    clients = r.json()
    assert any(c["client_type"] == "web" for c in clients)
    r2 = client.get("/api/admin/events", headers=h)
    assert r2.status_code == 200
