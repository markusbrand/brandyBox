## 1. Unit Testing and Reproduction

- [x] 1.1 Add unit test in `client-tauri/src-tauri/src/sync.rs` asserting that when server file deletion fails during `run_sync`, a `SyncSummary` with `status: "failed"` is enqueued and telemetry flush is executed.
- [x] 1.2 Verify the reproduction test fails or demonstrates missing summary before the fix.

## 2. Desktop Client Implementation

- [x] 2.1 Update `run_sync` in `client-tauri/src-tauri/src/sync.rs` on `client.delete_file` error to call `enqueue_sync_summary` with `status: "failed"` and invoke `flush_telemetry_queue(client)`.
- [x] 2.2 Verify that all tests pass.

## 3. Verification and Quality Assurance

- [x] 3.1 Run `cargo test` in `client-tauri/src-tauri` and verify all tests pass.
- [x] 3.2 Run repo-wide QA checks and confirm no regressions.
