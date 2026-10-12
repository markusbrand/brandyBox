## 1. Unit Testing and Reproduction

- [x] 1.1 Add regression test in `client-tauri/src-tauri/src/sync.rs` asserting that hash-matched and resumed downloads are retained in `completed_downloads` and saved in `state.paths`
- [x] 1.2 Add regression test in `client-tauri/src-tauri/src/sync.rs` asserting that bare `.git` files and `sub/.git` files are ignored by `is_ignored`

## 2. Desktop Client Implementation

- [x] 2.1 Update the download loop in `client-tauri/src-tauri/src/sync.rs` to register hash-matched and resumed paths into `completed_downloads` before continuing
- [x] 2.2 Update `is_ignored` in `client-tauri/src-tauri/src/sync.rs` to match bare `.git` files (`normalized == ".git"` and `normalized.ends_with("/.git")`)

## 3. Verification and QA

- [x] 3.1 Run `cargo test` in `client-tauri/src-tauri` and verify all tests pass
- [x] 3.2 Run full QA suite (`pytest backend` and `npm run build` in `client-tauri`) to verify no regressions
