## 1. Sync Concurrency and Mutual Exclusion

- [x] 1.1 Implement atomic mutual exclusion guard in `client-tauri/src-tauri/src/sync.rs` and verify with unit tests
- [x] 1.2 Update `run_sync` command and background sync loop in `client-tauri/src-tauri/src/lib.rs` to check sync lock and verify cargo test passes

## 2. Background Sync Telemetry Reporting

- [x] 2.1 Add `client.client_ping` call to `spawn_background_sync_loop` in `client-tauri/src-tauri/src/lib.rs` and verify cargo test passes

## 3. UI Sync Warning State and Progress Recovery

- [x] 3.1 Update `client-tauri/src/Settings.tsx` to handle `warning` status, manage `syncStatus`, and render appropriate alert severity
- [x] 3.2 Verify frontend build via `npm run build` in `client-tauri`

## 4. Verification and QA

- [x] 4.1 Run full project QA suite `./scripts/run-qa.sh` and ensure all cargo, frontend, backend, and documentation checks pass
