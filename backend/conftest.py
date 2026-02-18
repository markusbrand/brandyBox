"""Pytest configuration: set test env before any app imports so DB and JWT use test values."""

import asyncio
import os
import tempfile

import pytest

# Set before app.db.session or app.config are used so engine and settings use test paths
_tmp = tempfile.mkdtemp(prefix="brandybox_test_")
_db_path = os.path.join(_tmp, "test.db")
os.environ.setdefault("BRANDYBOX_DB_PATH", _db_path)
os.environ.setdefault("BRANDYBOX_JWT_SECRET", "test-jwt-secret-at-least-32-characters-long")
# Bootstrap admin for API tests (login as test@example.com / testpass123)
os.environ.setdefault("BRANDYBOX_ADMIN_EMAIL", "test@example.com")
os.environ.setdefault("BRANDYBOX_ADMIN_INITIAL_PASSWORD", "testpass123")


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop for async tests and DB init."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def init_test_db(event_loop):
    """Create tables once per test session."""
    from app.db.session import init_db
    from app.users.models import User  # noqa: F401 - register with Base

    event_loop.run_until_complete(init_db())


@pytest.fixture
def session_factory(init_test_db):
    """Yield get_session so tests can use async with session_factory() as session."""
    from app.db.session import get_session
    return get_session
