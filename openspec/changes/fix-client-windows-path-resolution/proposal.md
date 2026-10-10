## Why

In the Tauri desktop client (`client-tauri`), configuration paths and sync folder paths expanded via `expand_tilde` on Windows fail to strip leading backslashes (`\`). On Windows, Rust's `Path::join` treats any path starting with a backslash as a root-relative path (e.g. `\brandyBox`), replacing the user's home directory path (`C:\Users\<user>`) with the drive root (`C:\brandyBox` or `C:\`). Additionally, `safe_local_path` in `sync.rs` previously replaced only forward slashes with the platform separator, causing remote paths that contain backslashes to resolve as literal backslash filenames on Unix/macOS rather than hierarchical subdirectories.

Fixing these path resolution defects ensures consistent, cross-platform confinement of client sync folders and files.

## What Changes

- Modify `expand_tilde` in `client-tauri/src-tauri/src/config.rs` to trim both forward slashes and backslashes (`/` and `\`) when expanding paths prefixed with `~`, returning `home` directly if no subpath remains, and otherwise appending the normalized relative subpath to the home directory.
- Update `safe_local_path` in `client-tauri/src-tauri/src/sync.rs` to construct local target paths by pushing validated path segments onto the root, ensuring both `/` and `\` separators properly produce platform-native directory hierarchies across Windows, macOS, and Linux.
- Add unit tests covering tilde path expansion (`~`, `~/`, `~\`, `~/brandyBox`, `~\brandyBox`, `~\\brandyBox`) and multi-separator local path resolution.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `desktop-client`: Update path confinement and tilde expansion requirements to handle Windows backslashes and normalize multi-platform separators.

## Impact

- Affected files: `client-tauri/src-tauri/src/config.rs`, `client-tauri/src-tauri/src/sync.rs`.
- No API breaking changes. No external dependencies added.
