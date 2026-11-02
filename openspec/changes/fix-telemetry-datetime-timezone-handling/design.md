## Context

See `proposal.md` for motivation. SQLite stores and returns datetime values without timezone information by default, resulting in offset-naive Python `datetime` objects. When SQLAlchemy ORM executes `session.execute(delete(...))` within a session containing recently flushed rows, it uses `synchronize_session='evaluate'`, which evaluates the SQL where clause in Python against objects in the session's identity map. If the where clause compares against an offset-aware datetime (such as `cutoff = datetime.now(timezone.utc) - timedelta(days=days)`), Python raises `TypeError: can't compare offset-naive and offset-aware datetimes`. Additionally, sorting timelines in `brandybox-doctor` fails if entries contain mixed naive and aware datetimes.

## Goals / Non-Goals

**Goals:**
- Eliminate `TypeError` crashes during `log_server_event` and telemetry batch ingestion pruning.
- Prevent timeline sort crashes in `brandybox-doctor --trace` and `brandybox-doctor --llm-prompt`.
- Ensure telemetry test cases use dynamic relative timestamps so they do not expire under retention policies.

**Non-Goals:**
- Altering the SQLite database schema or migration scripts.
- Modifying client-side payload formats.

## Decisions

### Decision 1: Set `synchronize_session=False` on retention cleanup queries
Bulk deletion queries in `prune_telemetry_records` do not need ORM session synchronization because they delete expired records (e.g. older than 30 days) rather than currently active session entities. Setting `.execution_options(synchronize_session=False)` prevents SQLAlchemy from performing Python-side condition evaluation on in-memory objects.

### Decision 2: Set explicit UTC timestamps on `ServerEvent` creation
`log_server_event` will pass `created_at=datetime.now(timezone.utc)` explicitly instead of relying on `server_default=func.now()`, ensuring the Python object in session memory is always timezone-aware UTC.

### Decision 3: Normalize naive datetimes during ingestion and timeline sorting
In `ingest_telemetry_batch`, any event or summary timestamp lacking `tzinfo` is coerced to UTC using `.replace(tzinfo=timezone.utc)`. In `doctor.py`, timeline sort keys normalize timestamps through a helper function before comparison.

## Risks / Trade-offs

- [Risk: In-memory session staleness with `synchronize_session=False`] → Mitigation: Telemetry pruning targets records older than the retention threshold (e.g., 30 days), which never overlaps with newly created session rows.
- [Risk: Client sends local time without timezone] → Mitigation: Assuming UTC for naive timestamps (`.replace(tzinfo=timezone.utc)`) is standard across BrandyBox APIs and preserves chronological consistency.
