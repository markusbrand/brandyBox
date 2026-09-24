## Context

In `client-tauri/src-tauri/src/sync.rs`, the synchronization engine performs synchronization through several distinct steps:
1. Scan local files (`local_list = list_local(local_root)`).
2. Fetch remote files (`client.list_files()`).
3. Compute deletions:
   - `to_delete_remote = last_synced.difference(&current_local)`
   - `to_delete_local = last_synced.difference(&current_remote)`
4. Propagate deletions (deleting files on server and deleting files locally).
5. Build `to_download` list, with `to_download.retain(|path| !to_del_remote_set.contains(path))`.
6. Build `to_upload` list from `local_list`.

Because `local_list` is scanned at step 1 before local deletions occur in step 4, files deleted locally in step 4 still exist in `local_list`. When `to_upload` filters `local_list`, it checks `remote_by_item.get(path)`. Because the file was deleted on the server, `remote_by_item` does not contain it (`None`), causing the filter to return `true` (treating it as a newly created local file). During upload iteration, `full.exists()` returns `false`, causing the sync engine to log a warning, add the path to `skipped_uploads`, and transition the sync status to `Warning`.

## Goals / Non-Goals

**Goals:**
- Prevent files identified in `to_del_local_set` from ever being scheduled in `to_upload`.
- Match the symmetrical guarantee already provided by `to_download.retain(|path| !to_del_remote_set.contains(path))`.
- Prevent false skipped upload warnings and erroneous warning statuses on remote deletions.
- Add unit test coverage verifying that remote deletions do not produce upload candidates.

**Non-Goals:**
- Altering conflict resolution semantics for simultaneously edited and deleted files.
- Refactoring `run_sync` into smaller functions.

## Decisions

### Decision 1: Filter `to_del_local_set` during `to_upload` candidate collection

Filter out any path present in `to_del_local_set` when constructing `to_upload`:
```rust
let to_upload: Vec<String> = local_list
    .iter()
    .filter(|(path, _)| !is_ignored(path) && !to_del_local_set.contains(path.as_str()))
    .filter(|(path, local_mtime)| { ... })
```

*Rationale*:
- `to_del_local_set` is a `HashSet<String>` already constructed in `run_sync`.
- Membership lookup is $O(1)$.
- It mirrors the logic of `to_download.retain(|path| !to_del_remote_set.contains(path))` exactly.
- It prevents missing files from entering the upload pipeline, avoiding the false upload attempt and subsequent warning.

*Alternatives considered*:
- Rescanning `local_list` after local deletions: Unnecessary disk I/O and slower performance on large trees.
- Ignoring missing files in `skipped_uploads`: Would hide true race condition errors if a user deletes an actual pending upload file while sync is in progress.

## Risks / Trade-offs

- **[Risk]** A file deleted on remote is simultaneously modified locally.
  - **Mitigation**: Existing deletion logic already prioritizes remote deletion when a file was previously in `last_synced` and missing from `current_remote`. This change does not alter deletion determination, only prevents deleted files from generating false upload warnings.
