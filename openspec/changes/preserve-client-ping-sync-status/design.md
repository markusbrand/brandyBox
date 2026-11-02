## Context

See `proposal.md` for motivation. Currently, `upsert_client_ping` in `backend/app/telemetry/service.py` executes:
```python
stmt = stmt.on_conflict_do_update(
    index_elements=['user_email', 'client_type'],
    set_=dict(
        client_version=stmt.excluded.client_version,
        last_seen_at=stmt.excluded.last_seen_at,
        last_sync_at=stmt.excluded.last_sync_at,
        last_sync_ok=stmt.excluded.last_sync_ok,
        backend_version_at_ping=stmt.excluded.backend_version_at_ping,
    )
)
```
When a client ping supplies `last_sync_at=None` or `last_sync_ok=None`, SQLite directly overwrites `ClientConnection.last_sync_at` and `ClientConnection.last_sync_ok` with NULL.

## Goals / Non-Goals

**Goals:**
- Preserve existing `last_sync_at` and `last_sync_ok` in `client_connections` when incoming ping omits sync status.
- Allow new sync status (including `last_sync_ok = False`) to update properly whenever provided.
- Maintain single SQL roundtrip performance (`ON CONFLICT DO UPDATE`).

**Non-Goals:**
- Adding dedicated reset endpoints or schema migrations to `client_connections`.
- Changing how web or desktop clients construct ping requests.

## Decisions

### Decision 1: Use `func.coalesce` in `on_conflict_do_update`
- **Choice**:
  ```python
  last_sync_at=func.coalesce(stmt.excluded.last_sync_at, ClientConnection.last_sync_at),
  last_sync_ok=func.coalesce(stmt.excluded.last_sync_ok, ClientConnection.last_sync_ok),
  ```
- **Rationale**: In SQL standard and SQLite, `COALESCE(new_val, old_val)` evaluates to `new_val` when `new_val IS NOT NULL`, and falls back to `old_val` when `new_val IS NULL`. For booleans, `FALSE` (0) is a non-null value, so failed syncs (`last_sync_ok=False`) correctly overwrite previous states.
- **Alternatives Considered**:
  - *Read-before-write in Python*: Query existing record, merge fields in application code, and issue update. Rejected because it doubles DB roundtrips and introduces race conditions under concurrent pings.
  - *CASE expression*: `case((stmt.excluded.last_sync_at.isnot(None), stmt.excluded.last_sync_at), else_=ClientConnection.last_sync_at)`. Functionally identical to `coalesce`, but `coalesce` is cleaner and standard in SQL.

## Risks / Trade-offs

- [Risk] If a client intentionally wanted to clear/reset sync state back to NULL via ping, `coalesce` would prevent this.
  → Mitigation: Sync state in `ClientConnection` represents "last known sync outcome", which should persist across client restarts and presence pings. Resetting sync status is not a supported or required client operation.
