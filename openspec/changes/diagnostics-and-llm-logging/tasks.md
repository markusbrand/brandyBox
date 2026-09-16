## 1. Backend Telemetry Data Layer & Middleware

- [ ] 1.1 Create `SyncSummary` and `DiagnosticEvent` database models in `backend/app/telemetry/models.py` with SQLite table definitions and retention cleanup, and verify via SQLAlchemy session test.
- [ ] 1.2 Implement `X-Sync-ID` correlation middleware in `backend/app/main.py` and bind trace IDs to request logs, and verify via test request with header.
- [ ] 1.3 Add ingestion endpoint `POST /api/telemetry/events` and admin query endpoints in `backend/app/telemetry/routes.py`, and verify using pytest.

## 2. Raspberry Pi CLI Inspector (`brandybox-doctor`)

- [ ] 2.1 Implement `backend/app/cli/doctor.py` supporting `--summary`, `--trace <id>`, and `--llm-prompt` commands, and verify CLI outputs correctly on test database rows.
- [ ] 2.2 Add Docker container wrapper script and executable symlink for `brandybox-doctor` to enable direct invocation via `ssh pi`, and verify script execution.

## 3. Client Correlation & Telemetry Pipeline (`client-tauri`)

- [ ] 3.1 Implement unique `trace_id` generation per sync run and inject `X-Sync-ID` header into all HTTP sync requests in `client-tauri/src-tauri/src/api.rs`, and verify header inclusion.
- [ ] 3.2 Add structured error event classification and sync run summary creation in `client-tauri/src-tauri/src/sync.rs`, and verify payloads contain error codes, stages, and file metadata.
- [ ] 3.3 Implement persistent offline telemetry queue with automatic retry and flush to `POST /api/telemetry/events`, and verify queued items persist across restarts.

## 4. Web Admin Dashboard & LLM Export

- [ ] 4.1 Add API client methods in `web/src/api/http.ts` for fetching sync summaries and diagnostic events, and verify TypeScript compiles without errors.
- [ ] 4.2 Build Client Sync Matrix and searchable Error Event Feed in `web/src/pages/SettingsPage.tsx`, and verify rendering of client health statuses.
- [ ] 4.3 Implement "Copy LLM Context" clipboard export action generating structured markdown prompts, and verify clipboard content matches the LLM prompt template.

## 5. End-to-End Verification

- [ ] 5.1 Run full backend test suite (`pytest backend/`) and ensure all new and existing tests pass.
- [ ] 5.2 Validate end-to-end sync failure reporting from client to backend, verify `brandybox-doctor --llm-prompt` output, and confirm web dashboard displays the failure.
