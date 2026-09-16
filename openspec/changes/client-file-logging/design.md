## Context

The `client-tauri` desktop application uses `log` crate macros (`log::info!`, `log::warn!`, `log::error!`) and `eprintln!` across the sync engine (`sync.rs`), API client (`api.rs`), and lifecycle controller (`lib.rs`). However, no logging backend is initialized in `tauri::Builder`. In release desktop builds on macOS, standard output and error are redirected to `/dev/null` by the window system. When errors occur (such as 60s/100s sync timeouts or 401/403 network rejections), no diagnostic trail exists on the system.

## Goals / Non-Goals

**Goals:**
- Initialize `tauri-plugin-log` in `client-tauri` to capture all Rust `log` crate events.
- Write rotating log files to the standard OS log directory:
  - macOS: `~/Library/Logs/rocks.brandstaetter.brandybox/`
  - Linux: `~/.local/state/brandybox/logs/` or `~/.config/brandybox/logs/`
  - Windows: `%APPDATA%\BrandyBox\logs\`
- Configure log rotation with 5 MB maximum file size and a retention cap of 5 historical files.
- Add a Tauri command `open_logs_folder` that reveals the active log folder in Finder / file explorer.
- Add an "Open Logs Folder" button in the Settings interface (`Settings.tsx`).
- Provide build & installation commands to update `/Applications/Brandy Box.app` on macOS.

**Non-Goals:**
- Cloud-hosted telemetry or remote crash reporting (e.g. Sentry) — logs remain local and private.
- Built-in full-text log viewer inside the web UI — opening the native folder in the user's default text editor/Finder is lighter and more versatile.

## Decisions

### Decision 1: Use `tauri-plugin-log` (v2)
- **Rationale**: `tauri-plugin-log` is the standard official logging plugin for Tauri 2. It integrates directly with `tauri::Builder`, automatically hooks into the standard Rust `log` crate macros already present in the codebase, formats records with timestamps and levels, and manages file rotation cleanly.
- **Alternatives considered**:
  - `tracing` + `tracing-appender`: Powerful, but requires rewriting existing `log::*` macros throughout `api.rs`, `sync.rs`, and `lib.rs`.
  - Manual file writing in a thread/mutex: Reinventing file rotation, retention, formatting, and cross-platform log directory resolution.

### Decision 2: Platform Log Directory Resolution
- **Rationale**: Rely on Tauri's `app.path().app_log_dir()` to adhere to OS standards:
  - macOS: `~/Library/Logs/rocks.brandstaetter.brandybox/`
  - Linux: `~/.local/state/rocks.brandstaetter.brandybox/`
  - Windows: `%LOCALAPPDATA%\rocks.brandstaetter.brandybox\logs\`
- **Alternatives considered**: Storing logs in `~/.config/brandybox/` — violates macOS standard where user-facing application logs belong in `~/Library/Logs`.

### Decision 3: Expose "Open Logs Folder" in Settings UI
- **Rationale**: Users who encounter errors can click one button in the Settings window to immediately open Finder at the log location and inspect or attach logs.
- **Alternatives considered**: Forcing users to manually navigate hidden folders (`~/Library/Logs` is hidden by default in macOS Finder).

## Risks / Trade-offs

- **[Risk] Uncontrolled log growth during network outage**: If background sync runs continuously and errors every minute, log files could grow rapidly.
  - *Mitigation*: Configure `tauri-plugin-log` with max file size (5MB) and rotation keep count (5 files). Total disk usage will never exceed 25–30 MB.
- **[Risk] Sensitive data leakage in log files**: Logging tokens or user passwords.
  - *Mitigation*: Ensure no auth token, password, or sensitive request header is passed to `log::*` statements. `ApiClient` already excludes tokens from log statements.
