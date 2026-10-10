## Context

Brandy Box stores user files under `<storage_base_path>/<user_email>/`. In addition to user-uploaded files, this directory tree houses internal system directories:
- `.uploads`: Staging area for chunked file uploads.
- `.brandybox`: Server-side user preferences and assets (such as custom web UI background images).

While `.uploads` was previously blocked from `resolve_user_path` and filtered in recursive directory traversals, `.brandybox` was introduced without corresponding storage isolation filters. Consequently, `.brandybox` contents appeared in `GET /api/files/list` and `GET /api/files/folders`, leaked to desktop clients during sync, and allowed destructive actions via file endpoints.

## Goals / Non-Goals

**Goals:**
- Hide `.brandybox` and `.uploads` from `list_files_recursive` and `list_directories_recursive`.
- Reject any user-initiated access to `.brandybox` or `.uploads` via `resolve_user_path`.
- Allow the background image service in `background_image.py` to store and access its assets without using the restricted `resolve_user_path`.
- Prevent desktop sync in `client-tauri` from uploading or syncing local `.brandybox` or `.uploads` folders.
- Ensure all existing and new tests pass.

**Non-Goals:**
- Moving the `.brandybox` directory outside of the user's base storage path.
- Modifying image upload validation or formats.

## Decisions

### Decision 1: Declare `INTERNAL_DIRS` constant in `app.files.storage`

Declare `INTERNAL_DIRS = {".uploads", ".brandybox"}` in `backend/app/files/storage.py`.
In `resolve_user_path`:
```python
if safe in INTERNAL_DIRS:
    raise ValueError("Access to internal directory is denied")
```
In `list_files_recursive` and `list_directories_recursive`:
```python
if entry.name in INTERNAL_DIRS:
    continue
```

*Rationale*:
- Consolidates internal directory names into a single set.
- Completely prevents directory traversal or file manipulation into internal directories.
- Fast $O(1)$ set lookup during filesystem scanning.

### Decision 2: Update `_user_brandybox_dir` in `app.users.background_image`

Change `_user_brandybox_dir` to compute `user_base_path(email) / _REL_FOLDER` directly rather than invoking `resolve_user_path(email, _REL_FOLDER)`.

*Rationale*:
- `resolve_user_path` is designed to validate untrusted, user-supplied relative path parameters from API requests.
- System services creating or accessing internal directories have trusted internal knowledge and should construct internal paths relative to `user_base_path`.

### Decision 3: Add internal directory check to desktop client `is_ignored`

In `client-tauri/src-tauri/src/sync.rs`, check for `.brandybox` and `.uploads` paths in `is_ignored`.

*Rationale*:
- Defense-in-depth: Even if a client encounters an older backend or local directory created by an older version, the desktop client will never upload, delete, or sync these internal directories.

## Risks / Trade-offs

- **[Risk]** Existing desktop clients might have downloaded `.brandybox/content-bg.png` locally before this fix.
  - **Mitigation**: Once the server stops listing `.brandybox` in `list_files()`, future sync runs with updated clients ignore `.brandybox`. Adding `.brandybox` to `is_ignored` ensures local `.brandybox` files are ignored by sync.
