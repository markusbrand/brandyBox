## 1. Backend Implementation

- [x] 1.1 Update `upsert_client_ping` in `backend/app/telemetry/service.py` to use `func.coalesce` for `last_sync_at` and `last_sync_ok`
- [x] 1.2 Add regression unit test in `backend/tests/test_web_features.py` verifying sync status is preserved when subsequent ping omits sync status

## 2. Verification

- [x] 2.1 Run `pytest` on backend test suite to ensure all tests pass and no regressions occur
