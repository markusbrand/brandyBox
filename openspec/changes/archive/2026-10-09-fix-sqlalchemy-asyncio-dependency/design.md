## Context

The backend uses `sqlalchemy.ext.asyncio` with `aiosqlite` for database access. SQLAlchemy 2.0+ delegates async execution to `greenlet`. In recent releases on PyPI (such as 2.1.1), `greenlet` is no longer installed as an implicit sub-dependency of unadorned `sqlalchemy`.

When running in clean Python environments without pre-cached wheels (such as Ubuntu GitHub Actions runners or container images), installing from `backend/requirements.txt` leaves out `greenlet`, resulting in runtime `ImportError` on any import of `sqlalchemy.ext.asyncio`.

## Goals / Non-Goals

**Goals**:
- Ensure all required packages for SQLAlchemy's asyncio mode are pinned and declared in `backend/requirements.txt`.
- Unblock CI backend tests on GitHub Actions.
- Ensure Docker container builds and clean virtual environments install smoothly without missing dependency errors.

**Non-Goals**:
- Upgrade or rewrite database access patterns.
- Change database engines or ORM frameworks.

## Decisions

- Update line in `backend/requirements.txt`:
  Change `sqlalchemy>=2.0.51` to `sqlalchemy[asyncio]>=2.0.51`.
  Also add `greenlet>=3.0.0` explicitly to guarantee compatibility even if wheel resolution or pip flags omit optional extras.

## Verification

- Run `pip install -r backend/requirements.txt` in a fresh virtualenv or verify dependency resolution with `pip install --dry-run`.
- Run `pytest` locally to confirm all tests collect and pass cleanly.
