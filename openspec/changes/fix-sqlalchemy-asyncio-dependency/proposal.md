## Why

Recent releases of SQLAlchemy (version 2.1+) on PyPI no longer install `greenlet` as an implicit dependency when installing unadorned `sqlalchemy`. Because BrandyBox utilizes `sqlalchemy.ext.asyncio` (`AsyncSession`, `async_sessionmaker`, `create_async_engine`), SQLAlchemy requires the `greenlet` library at runtime. Without specifying the `[asyncio]` extra in `backend/requirements.txt`, clean environments (such as GitHub Actions CI runners and production Docker containers) fail during test collection and server startup with `ImportError: The SQLAlchemy asyncio module requires that the Python 'greenlet' library is installed`.

## What Changes

- Update `backend/requirements.txt` to specify `sqlalchemy[asyncio]>=2.0.51` (and `greenlet>=3.0.0`) so that `greenlet` is explicitly installed alongside SQLAlchemy in all environments.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
<!-- None. Spec-level behavior is unchanged; skip_specs: true is enabled in .openspec.yaml. -->

## Impact

- Affects `backend/requirements.txt`.
- Unblocks GitHub Actions CI (`Test/Backend (pytest)`) and ensures fresh developer or container setups reliably have required asyncio dependencies installed.
