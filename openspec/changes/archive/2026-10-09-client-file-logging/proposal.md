## Why

When users encounter errors on the installed desktop app (such as background sync timeouts, Cloudflare connection aborts, or authentication refresh failures), no diagnostic log files exist on disk to troubleshoot the issue. On macOS and Linux, GUI application processes launched by system launchers redirect standard output and standard error to `/dev/null`, and the Tauri client currently lacks a configured logging backend for the `log` crate. Introducing persistent rotating file logging and a Settings UI button to open logs ensures that errors can be inspected and diagnosed.

## What Changes

- **Persistent Rotating File Logger**: Initialize `tauri-plugin-log` (or equivalent file-backed logging provider) in `client-tauri` configured to write formatted, timestamped log messages (`[timestamp] [level] [target] message`) to platform-standard directories.
  - macOS: `~/Library/Logs/rocks.brandstaetter.brandybox/`
  - Linux: `~/.local/state/brandybox/logs/` or `~/.config/brandybox/logs/`
  - Windows: `%APPDATA%\BrandyBox\logs\`
- **Log Level and Rotation**: Configure log levels (Info in release, Debug in dev), max file size limits (e.g., 5 MB per file), and max file retention (e.g., keep last 5 logs) to prevent unbounded disk usage.
- **Logging Tauri Commands & UI Action**: Expose a Tauri command `open_logs_folder` and add a button in the Settings window ("Open Logs Folder") to let users easily view and share diagnostic logs.
- **Mac App Build & Packaging Documentation**: Document and script macOS app build and installation procedures so updates can be deployed cleanly over `/Applications/Brandy Box.app`.

## Capabilities

### New Capabilities
- `client-logging`: Defines persistent file logging, log level formatting, log rotation limits, and UI log folder access for the desktop client application.

### Modified Capabilities
<!-- None -->

## Impact

- **Client Rust Backend**: `client-tauri/src-tauri/Cargo.toml` (adds `tauri-plugin-log`), `client-tauri/src-tauri/src/lib.rs` (logger initialization in builder, `open_logs_folder` command), `capabilities/default.json` (log plugin permissions).
- **Client Frontend**: `client-tauri/src/Settings.tsx` (adds "Open Logs" button in Settings UI).
- **Packaging/Docs**: `docs/client/tauri.md` and macOS build instructions.
