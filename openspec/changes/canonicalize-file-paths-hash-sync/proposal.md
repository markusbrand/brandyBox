## Why

In `backend/app/files/routes.py`, `_normalize_path_param` does not strip leading or trailing slashes, redundant slashes, or normalize path separators. When clients provide a relative path with a leading slash (e.g. `path=/folder/file.txt`), backslashes (`path=folder\file.txt`), or redundant separators, the file storage layer (`resolve_user_path`) strips the slashes and resolves the physical file to `folder/file.txt`, but `routes.py` persists the raw unnormalized path `"/folder/file.txt"` into the `file_hashes` database table.

Because `GET /api/files/list` dynamically traverses the filesystem using `list_files_recursive` (which produces clean, relative paths like `"folder/file.txt"`), the SQL query `WHERE path IN ('folder/file.txt')` fails to match the stored `"/folder/file.txt"`. Consequently:
1. `GET /api/files/list` returns files without their computed SHA-256 hash (`hash: None`), breaking desktop client hash-based change detection and forcing redundant re-downloads or re-uploads.
2. When the client or user deletes the file via `DELETE /api/files/delete?path=folder/file.txt`, `delete_hash` attempts to delete `"folder/file.txt"`, leaving the row `"/folder/file.txt"` as an orphaned zombie record in the database indefinitely.
3. Overwriting a file with a smaller file when user storage usage is low can cause `current_user.storage_used_bytes` to underflow into negative numbers because clamp-to-zero logic is missing in upload handlers.

## What Changes

- Update `_normalize_path_param` in `backend/app/files/routes.py` to canonicalize relative file paths by replacing backslashes with forward slashes, stripping leading/trailing slashes, and removing empty segments.
- In `upload_init`, save the canonical relative path into the `.path` metadata file.
- In `upload_finalize` and `upload_file`, persist and return the canonical relative path derived from `target.relative_to(base).as_posix()` and store the hash under this canonical path.
- In `upload_file` and `upload_finalize`, ensure `current_user.storage_used_bytes` is clamped to at least 0 when diff is negative.
- In `delete_file`, delete the hash using the canonical relative path.
- Add comprehensive unit tests in `backend/tests/test_files_routes.py` and `backend/tests/test_upload_streaming.py` asserting that unnormalized query parameters (leading slashes, Windows backslashes, duplicate slashes) store canonical paths, return hashes in file listings, and properly delete hashes on file removal.

## Capabilities

### Modified Capabilities
- `file-storage`: Enforce canonical relative path normalization across file upload, finalize, list, and delete operations to ensure consistent hash lookup and database integrity.

## Impact

- **Affected code**: `backend/app/files/routes.py`, `backend/tests/test_files_routes.py`, `backend/tests/test_upload_streaming.py`
- **APIs**:
  - `POST /api/files/upload`: Returns canonical relative path in JSON response.
  - `POST /api/files/upload/finalize`: Returns canonical relative path in JSON response.
  - `GET /api/files/list`: Returns SHA-256 hashes consistently for all files regardless of how the path parameter was formatted at upload time.
  - `DELETE /api/files/delete`: Deletes corresponding hash row from database cleanly.
- **Dependencies**: No new external dependencies.
