## 1. Backend Telemetry Service Fixes

- [x] 1.1 In `backend/app/telemetry/service.py`, set `synchronize_session=False` on retention delete queries and pass explicit UTC `created_at` on `ServerEvent` instantiation; verify via unit test.
- [x] 1.2 In `backend/app/telemetry/service.py`, normalize incoming event and summary timestamps to timezone-aware UTC in `ingest_telemetry_batch`; verify with test ingestion of naive timestamps.

## 2. Doctor CLI Timeline Normalization

- [x] 2.1 In `backend/app/cli/doctor.py`, normalize timeline timestamps to UTC before sorting in `show_trace` and `generate_llm_prompt`; verify timeline output with mixed timestamps.

## 3. Telemetry Test Suite & Regression Verification

- [x] 3.1 Update `backend/tests/test_telemetry.py` to use relative UTC timestamps in `test_telemetry_api_routes` and add test cases for `log_server_event` pruning and naive datetime ingestion; verify with `pytest backend/tests/test_telemetry.py`.
- [x] 3.2 Run full QA suite (`./scripts/run-qa.sh` and `pytest backend`) to verify zero regressions across the codebase.
