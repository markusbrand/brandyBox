## Context

In Brandy Box, files are stored on disk under each user's directory (`<storage_base_path>/<user_email>/...`). File content hashes (SHA-256) are computed upon upload and cached in the SQLite `file_hashes` table with composite key `(user_email, path)`. The file listing endpoint (`GET /api/files/list`) uses `list_files_recursive` to scan the filesystem and batches hash lookups using `get_hashes_for_paths`.

Currently, `_normalize_path_param` in `backend/app/files/routes.py` fails to strip leading or redundant slashes or normalize Windows separators (`\`). While `resolve_user_path` strips slashes to find the file on disk, `routes.py` uses the raw unnormalized `path_param` when saving to `file_hashes` and returning to the client. This mismatch breaks hash lookups in `list_files` and leaves orphaned rows upon deletion.

See `proposal.md` for motivation and `specs/file-storage/spec.md` for requirements.

## Goals / Non-Goals

**Goals:**
- Ensure all file route operations (`upload_init`, `upload_file`, `upload_finalize`, `download_file`, `delete_file`) use canonical relative paths (`docs/file.txt`).
- Persist hashes in `file_hashes` strictly with the canonical relative path matching `list_files_recursive`.
- Ensure `delete_file` purges any matching hash from `file_hashes`, even if the file on disk was already deleted.
- Clamp `current_user.storage_used_bytes` to 0 when overwriting files with smaller sizes.

**Non-Goals:**
- Changing database schema or adding new database tables.
- Modifying desktop client sync protocol or API contracts.

## Decisions

### Decision 1: Robust Path Normalization in `_normalize_path_param`
Update `_normalize_path_param(path: Optional[str]) -> str` to:
1. Return `""` if `path` is empty or None.
2. Replace `\` with `/`.
3. Split on `/` and strip leading/trailing whitespace from each segment while preserving valid filename characters like `+`.
4. Filter out empty segments and rejoin with `/`.

*Rationale*:
- Centralizes path string sanitization for all query parameter inputs.
- Preserves filename characters like `+` while eliminating leading slashes (`/a/b` -> `a/b`), trailing slashes (`a/b/` -> `a/b`), duplicate slashes (`a//b` -> `a/b`), and Windows separators (`a\b` -> `a/b`).

### Decision 2: Canonicalize from Resolved Path Target
In `upload_file` and `upload_finalize`:
Derive the canonical relative path directly from the resolved filesystem target:
`canonical_path = target.relative_to(user_base_path(current_user.email)).as_posix()`
Use `canonical_path` for `set_hash` and for the returned `{"path": canonical_path}` JSON.

*Rationale*:
- Completely eliminates any discrepancy between the on-disk file location and the database hash record.
- Guarantees that `list_files_recursive` (which scans the exact same filesystem structure) will always produce matching path strings for `get_hashes_for_paths`.

### Decision 3: Storage Quota Underflow Protection
In `upload_file` and `upload_finalize`:
When applying size difference `current_user.storage_used_bytes += (size - old_size)`:
Ensure `current_user.storage_used_bytes = max(0, current_user.storage_used_bytes)`.

*Rationale*:
- Matches existing logic in `delete_file` (lines 553-554).
- Prevents database corruption from negative storage metrics.

## Risks / Trade-offs

- **[Risk]** Existing database might contain legacy rows with leading slashes (`/path/file.txt`).
  - **Mitigation**: Future uploads and updates write canonical paths. Deletions will cleanly match canonical paths.
