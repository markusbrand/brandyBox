"""Tests for user service: get_user_by_email, create_user, ensure_admin_exists."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.users.models import User, UserCreate
from app.users.service import ensure_admin_exists, create_user, get_user_by_email


@pytest.fixture
def mock_settings_no_smtp(monkeypatch):
    """Settings with no SMTP so create_user does not try to send email."""
    from app.users import service as svc
    mock = MagicMock()
    mock.smtp_host = ""
    mock.smtp_from = ""
    monkeypatch.setattr(svc, "get_settings", lambda: mock)


@pytest.mark.asyncio
async def test_get_user_by_email_none_when_empty_db(session_factory):
    """get_user_by_email returns None when no user exists."""
    async with session_factory() as session:
        user = await get_user_by_email(session, "nobody@example.com")
    assert user is None


@pytest.mark.asyncio
async def test_create_user_returns_user_and_temp_password(mock_settings_no_smtp, session_factory):
    """create_user creates user and returns (user, temp_password) when SMTP not configured."""
    async with session_factory() as session:
        payload = UserCreate(
            email="newuser@example.com",
            first_name="New",
            last_name="User",
        )
        user, temp_password = await create_user(session, payload, is_admin=False)
        await session.commit()
    assert user.email == "newuser@example.com"
    assert user.first_name == "New"
    assert user.last_name == "User"
    assert user.is_admin is False
    assert len(temp_password) >= 12
    assert user.password_hash


@pytest.mark.asyncio
async def test_create_user_duplicate_raises(mock_settings_no_smtp, session_factory):
    """create_user raises ValueError when user already exists."""
    async with session_factory() as session:
        payload = UserCreate(
            email="dup@example.com",
            first_name="D",
            last_name="U",
        )
        await create_user(session, payload, is_admin=False)
        await session.commit()
    async with session_factory() as session:
        with pytest.raises(ValueError, match="already exists"):
            await create_user(session, payload, is_admin=False)


@pytest.mark.asyncio
async def test_ensure_admin_exists_skips_when_no_env(session_factory):
    """ensure_admin_exists does nothing when admin_email or admin_initial_password not set."""
    from app.users import service as svc
    mock = MagicMock()
    mock.admin_email = ""
    mock.admin_initial_password = ""
    with patch.object(svc, "get_settings", return_value=mock):
        async with session_factory() as session:
            await ensure_admin_exists(session)
    # No user created
    async with session_factory() as session:
        u = await get_user_by_email(session, "admin@example.com")
    assert u is None


@pytest.mark.asyncio
async def test_ensure_admin_exists_creates_admin_when_set(session_factory):
    """ensure_admin_exists creates admin user when env is set and user does not exist."""
    from app.users import service as svc
    mock = MagicMock()
    mock.admin_email = "bootstrap@example.com"
    mock.admin_initial_password = "bootstrap-secret"
    with patch.object(svc, "get_settings", return_value=mock):
        async with session_factory() as session:
            await ensure_admin_exists(session)
            await session.commit()
    async with session_factory() as session:
        user = await get_user_by_email(session, "bootstrap@example.com")
    assert user is not None
    assert user.is_admin is True
    assert user.first_name == "Admin"
