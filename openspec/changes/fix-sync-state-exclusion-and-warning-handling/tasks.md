## 1. Unit Testing and Reproduction

- [x] 1.1 Add regression unit test `skipped_transfer_of_existing_file_excluded_from_synced_state` in `client-tauri/src-tauri/src/sync.rs` and verify it exposes candidate inclusion before the fix
- [x] 1.2 Update `base_synced` computation in `client-tauri/src-tauri/src/sync.rs` to exclude `to_download_set` and `to_upload_set` and verify tests pass

## 2. Desktop Client Implementation

- [x] 2.1 Update `run_sync` command in `client-tauri/src-tauri/src/lib.rs` to check for active sync status and prevent concurrent sync launches
- [x] 2.2 Update `Settings.tsx` to handle `warning` status in the `sync-status` event listener, reset `syncing` to false, clear `syncProgress`, reload settings, and display the warning alert

## 3. Verification and Quality Assurance

- [x] 3.1 Run full cargo test suite in `client-tauri/src-tauri` and verify all tests pass
- [x] 3.2 Run client frontend build (`npm run build` in `client-tauri`) and verify TypeScript compilation succeeds
- [x] 3.3 Run full QA test suite (`./scripts/run-qa.sh`) to ensure end-to-end repository health
