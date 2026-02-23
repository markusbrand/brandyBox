"""Tests for JWT and password hashing."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_subject_from_access,
    get_subject_from_refresh,
    hash_password,
    verify_password,
)


@pytest.fixture(autouse=True)
def _mock_settings(monkeypatch):
    """Provide test settings for JWT (secret and algorithm)."""
    from app.auth import jwt as jwt_mod
    mock = MagicMock()
    mock.jwt_secret = "test-secret-at-least-32-characters-long"
    mock.jwt_algorithm = "HS256"
    mock.access_token_expire_minutes = 30
    mock.refresh_token_expire_days = 365
    monkeypatch.setattr(jwt_mod, "get_settings", lambda: mock)


def test_hash_password_returns_bcrypt_hash() -> None:
    """Hashed password is a string and differs from plain."""
    plain = "mySecret123"
    hashed = hash_password(plain)
    assert isinstance(hashed, str)
    assert hashed != plain
    assert hashed.startswith("$2")  # bcrypt


def test_verify_password_correct() -> None:
    """Correct password verifies against hash."""
    plain = "mySecret123"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong() -> None:
    """Wrong password fails verification."""
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_password_longer_than_72_bytes_truncated() -> None:
    """Passwords longer than 72 bytes are truncated (bcrypt limit); verification still works."""
    long_plain = "a" * 100
    hashed = hash_password(long_plain)
    # Truncated to 72 bytes: first 72 chars verify
    assert verify_password("a" * 72, hashed) is True
    assert verify_password(long_plain, hashed) is True  # same after truncation


def test_create_access_token_decode() -> None:
    """Access token encodes subject and type 'access'; decode returns payload."""
    token = create_access_token("user@example.com")
    assert isinstance(token, str)
    payload = decode_token(token)
    assert payload is not None
    assert payload.get("sub") == "user@example.com"
    assert payload.get("type") == "access"
    assert "exp" in payload


def test_create_refresh_token_decode() -> None:
    """Refresh token has type 'refresh' and subject."""
    token = create_refresh_token("user@example.com")
    payload = decode_token(token)
    assert payload is not None
    assert payload.get("type") == "refresh"
    assert payload.get("sub") == "user@example.com"


def test_get_subject_from_access() -> None:
    """get_subject_from_access returns email for valid access token."""
    token = create_access_token("admin@test.co")
    assert get_subject_from_access(token) == "admin@test.co"


def test_get_subject_from_access_rejects_refresh_token() -> None:
    """get_subject_from_access returns None for refresh token."""
    token = create_refresh_token("user@test.co")
    assert get_subject_from_access(token) is None


def test_get_subject_from_refresh() -> None:
    """get_subject_from_refresh returns email for valid refresh token."""
    token = create_refresh_token("user@test.co")
    assert get_subject_from_refresh(token) == "user@test.co"


def test_get_subject_from_refresh_rejects_access_token() -> None:
    """get_subject_from_refresh returns None for access token."""
    token = create_access_token("user@test.co")
    assert get_subject_from_refresh(token) is None


def test_decode_token_invalid_returns_none() -> None:
    """Invalid or tampered token decodes to None."""
    assert decode_token("not-a-jwt") is None
    assert decode_token("") is None
    # Valid shape but wrong secret would be tested with another secret
