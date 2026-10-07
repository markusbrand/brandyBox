## 1. Implementation

- [x] 1.1 Update `expand_tilde` in `client-tauri/src-tauri/src/config.rs` to trim both `/` and `\` and safely return `home` when no subpath remains
- [x] 1.2 Update `safe_local_path` in `client-tauri/src-tauri/src/sync.rs` to build target paths by pushing validated segments onto the root
- [x] 1.3 Add unit tests in `client-tauri/src-tauri/src/config.rs` verifying `expand_tilde` for `~`, `~/`, `~\`, `~/brandyBox`, `~\brandyBox`, and `~\\brandyBox`
- [x] 1.4 Add unit tests in `client-tauri/src-tauri/src/sync.rs` verifying `safe_local_path` with backslash-separated paths

## 2. Verification

- [x] 2.1 Run `cargo test` in `client-tauri/src-tauri` and verify all unit tests pass
- [x] 2.2 Run `./scripts/run-qa.sh` and verify complete QA suite passes cleanly across all components
