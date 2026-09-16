## 1. Plugin Integration & Dependencies

- [x] 1.1 Add `tauri-plugin-log = "2"` to `client-tauri/src-tauri/Cargo.toml` and verify compilation with `cargo check`
- [x] 1.2 Add log plugin permissions to `client-tauri/src-tauri/capabilities/default.json` and verify capability configuration

## 2. Logger Initialization & File Rotation

- [x] 2.1 Initialize `tauri_plugin_log` in `client-tauri/src-tauri/src/lib.rs` with formatted timestamps, file rotation (5MB cap, 5 file retention), and log level filtering
- [x] 2.2 Verify that sync engine operations, retries, and errors emit persistent entries to `app_log_dir`

## 3. UI and Tauri Command for Log Access

- [x] 3.1 Implement `open_logs_folder` Tauri command in `client-tauri/src-tauri/src/lib.rs` to reveal the active log folder in Finder or default file explorer
- [x] 3.2 Add an "Open Logs Folder" action button in `client-tauri/src/Settings.tsx` and verify it invokes `open_logs_folder`

## 4. macOS Packaging & Installation

- [x] 4.1 Build production release binary and update `/Applications/Brandy Box.app` on this Mac to version 1.3.2+
- [x] 4.2 Verify `/Applications/Brandy Box.app` starts successfully, syncs with the 300s timeout, and creates log files in `~/Library/Logs/rocks.brandstaetter.brandybox/`
