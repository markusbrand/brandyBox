## Context

See proposal.md. The fixes span both backend file management (`backend/app/files/`) and desktop client operations (`client-tauri/src-tauri/src/`).

## Goals / Non-Goals

**Goals:**
- Fix `Cmd+Q` and menu bar "Quit" functionality on macOS while keeping background accessory mode when the settings window is closed.
- Allow plus-addressed email accounts (e.g. `user+tag@gmail.com`) to utilize all file storage APIs without server error.
- Isolate the internal `.uploads` scratch directory from public file and folder listings and prevent path resolution into it.
- Ensure macOS autostart LaunchAgent uses the resolved absolute binary path to successfully invoke Brandy Box on login.
- Safeguard file download temporary paths against truncation, stem collisions, and spurious re-uploading.

**Non-Goals:**
- Redesigning the chunked upload protocol or database schema.
- Changing autostart mechanisms on Windows or Linux beyond using `current_exe()`.
- Altering the existing sync conflict resolution algorithm.

## Decisions

### 1. Tauri ExitRequested Handling
- **Decision**: In `client-tauri/src-tauri/src/lib.rs`, match `tauri::RunEvent::ExitRequested { code, api, .. }` and call `api.prevent_exit()` only when `code.is_none()`.
- **Rationale**: In Tauri v2, `code` is `None` when triggered by closing the last window, and `Some(exit_code)` when triggered by an explicit quit event (Cmd+Q, Quit menu item, or OS shutdown). Checking `code.is_none()` allows user-directed quits to succeed while preventing exit when the window closes.
- **Alternative Considered**: Checking window count or intercepting menu items; rejected because `PredefinedMenuItem::quit` is an OS-level menu action handled by Tauri's run loop.

### 2. Email Path Sanitization
- **Decision**: Update `_SAFE_EMAIL` in `backend/app/files/storage.py` to `re.compile(r"^[a-zA-Z0-9_.@+-]+$")`.
- **Rationale**: The plus sign `+` is a standard, ubiquitous character in email addresses (RFC 5322) and safe on all modern filesystems (ext4, APFS, NTFS). It is already accepted by Pydantic's `EmailStr` and permitted in filenames by `_SAFE_SEGMENT_ASCII`.
- **Alternative Considered**: Hashing email addresses for folder names; rejected because it breaks backward compatibility with existing storage folder structures.

### 3. Upload Directory Isolation
- **Decision**:
  1. In `storage.py`, update `list_files_recursive` and `list_directories_recursive` to skip any directory entry where `entry.name == ".uploads"`.
  2. In `resolve_user_path`, verify that no path component is `".uploads"`.
- **Rationale**: Prevents internal temporary chunks and metadata from leaking into API responses (`/list`, `/folders`) and stops clients from reading or modifying in-flight upload chunks via `/download` or `/delete`.
- **Alternative Considered**: Storing uploads outside `user_base`; rejected because atomic `rename` / `shutil.move` across filesystem boundaries is not guaranteed if temp and target are on different mounts.

### 4. macOS Autostart Executable Path
- **Decision**: In `client-tauri/src-tauri/src/config.rs`, update `executable_command()` to use `std::env::current_exe()` across all platforms (with fallback to binary name).
- **Rationale**: Apple's `launchd` requires an absolute path in `ProgramArguments[0]`. `std::env::current_exe()` returns `/Applications/Brandy Box.app/Contents/MacOS/brandybox` or the current path, ensuring `launchd` can execute the binary.
- **Alternative Considered**: Hardcoding `/Applications/Brandy Box.app/Contents/MacOS/brandybox`; rejected because development builds and non-standard installs would fail to launch.

### 5. Download Temporary File Naming & Sync Filter
- **Decision**:
  1. In `api.rs`, format temporary download paths as `.{filename}.tmp_download` using `dest_path.with_file_name(format!(".{}.tmp_download", file_name))` and delete the temporary file on error.
  2. In `sync.rs`, update `is_ignored` to ignore any file matching `*.tmp_download` or starting with `.` if within sync ignore.
- **Rationale**: Prefixing with `.` and appending `.tmp_download` guarantees the temporary file has a distinct filename from the target (avoiding truncation if the target is named `*.tmp_download` or stem collisions like `doc.pdf` vs `doc.docx`). Adding it to sync ignore ensures abandoned temporary files are never uploaded to the server.
- **Alternative Considered**: Using OS temp directory (`/tmp`); rejected because cross-device renames across different filesystems would be non-atomic.

## Risks / Trade-offs

- **[Risk] Existing `.uploads` folder on disk**: Existing abandoned upload directories in user storage will no longer appear in file listings.
  - **Mitigation**: This is the intended behavior. A background maintenance cleaner can prune aged upload directories if needed.
- **[Risk] Path normalization in sync engine**: Files starting with `.` could potentially be ignored unintentionally.
  - **Mitigation**: Specifically filter `name.ends_with(".tmp_download")` rather than all dotfiles, preserving user dotfiles that aren't in `SYNC_IGNORE`.
