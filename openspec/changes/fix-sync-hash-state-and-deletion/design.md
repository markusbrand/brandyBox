## Context

The desktop client sync engine (`client-tauri/src-tauri/src/sync.rs`) maintains two-way synchronization between a local filesystem directory and the Brandybox backend. To track synchronization state across runs, the engine persists `SyncStateFile` containing `paths: Vec<String>` (files present at the end of the previous cycle) and `file_hashes: HashMap<String, String>` (SHA-256 content hashes).

When scheduling uploads and downloads, relying purely on timestamps is fragile due to client-server clock skew, archive extraction, or backups preserving historical timestamps. Previous attempts to prevent redundant work introduced inverted timestamp guards, stale cache checks, and incomplete state updates.

## Goals / Non-Goals

**Goals:**
- Provide robust, clock-skew resilient file synchronization using 3-way hash comparisons between local disk hash, server hash, and recorded base hash.
- Ensure locally edited files are always uploaded to the server when server content has not changed, regardless of whether local mtime is older or newer than server mtime.
- Verify actual disk file content before skipping downloads rather than relying on stale cache entries.
- Maintain accurate `file_hashes` state by updating on upload and pruning on deletion.
- Retain failed local deletions in sync state to prevent resurrection and re-uploading of deleted files.

**Non-Goals:**
- Implementing multi-version history branching or interactive manual merge conflict resolution.
- Modifying backend API endpoints or storage database models.

## Decisions

### 1. 3-Way Content Hash Reconciliation in Planning
When a file exists both locally and remotely and both hashes are available:
- If `local_hash == server_hash`: Contents are identical; omit from both upload and download queues, and update `state.file_hashes`.
- If `Some(server_hash) == state.file_hashes.get(path)` and `local_hash != server_hash`: The server copy has not changed since the last sync, so the local file was modified. Queue for `to_upload`, do not queue for `to_download`, regardless of timestamps.
- If `Some(local_hash) == state.file_hashes.get(path)` and `server_hash != local_hash`: The local copy has not changed since the last sync, so the server copy was modified. Queue for `to_download`, do not queue for `to_upload`.
- If neither hash matches (or base hash is unrecorded): Fall back to modification timestamps (`local_mtime > remote_mtime` uploads; otherwise downloads).

### 2. Live Disk Verification in Download Loop
In the download execution loop, remove the check that compares `state.file_hashes` against `remote_hashes`. Instead, check `compute_file_hash(&local_path).as_deref() == Some(hash.as_str())`. If the file on disk already matches the remote hash, skip redundant network transfer; otherwise, execute the download.

### 3. Update `file_hashes` on Successful Upload
After `client.upload_file_from_path(path, &full)` succeeds, compute the local file hash and insert it into `state.file_hashes`.

### 4. Prune `file_hashes` on File Deletion
When a file is removed locally via `to_del_local` or removed on the server via `to_del_remote`, remove its entry from `state.file_hashes`.

### 5. Retain Failed Local Deletions in Synced State
When `std::fs::remove_file(&full)` returns an error (e.g. file lock or permissions error):
- Record an error diagnostic event via `enqueue_diagnostic_event`.
- Append a warning to `warnings`.
- Retain the path in `base_synced` so that `state.paths` preserves it.
- On the next sync cycle, the file remains in `last_synced` and missing from `current_remote`, causing `to_del_local` to retry deletion rather than treating it as a new local file and re-uploading it.

## Risks / Trade-offs

- **Hashing overhead**: Computing SHA-256 for local files takes negligible time (<1ms for typical documents and photos) and is only performed when checking candidates that exist both locally and remotely.
- **Clock skew fallback**: When both sides were modified concurrently and conflict, mtime remains the final tie-breaker, matching Brandybox's last-write-wins design.
