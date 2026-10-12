## Context

In `client-tauri/src-tauri/src/sync.rs`, the synchronization engine constructs `base_synced` by filtering out all paths scheduled in `to_download_set` and `to_upload_set` (to ensure failed transfers are excluded from synchronized state). The persisted synchronized paths list (`state.paths`) is then constructed by `base_synced.union(completed_downloads).chain(completed_uploads)`.

In the download execution loop, when a file transfer is skipped because the local file's computed SHA-256 hash already matches the server's hash (`local_hash == *hash`) or because it was completed in an earlier interrupted run (`prev_downloaded`), the loop executes `continue;` without adding `path` to `completed_downloads`. Consequently, the file is dropped from `state.paths` (`sync_state.json`), leading to resurrection on subsequent sync cycles if deleted locally.

In addition, `is_ignored` checks `.git/` directory prefixes (`contains("/.git/")` and `starts_with(".git/")`) but fails to match bare `.git` files (`.git` or `*/.git`) produced by git submodules and worktrees.

## Goals / Non-Goals

**Goals:**
- Ensure files whose content is verified to match the server hash are recorded in `completed_downloads` and persisted in `state.paths`.
- Ensure previously completed downloads in resumed cycles are recorded in `completed_downloads` and persisted in `state.paths`.
- Keep failed or skipped (due to error/unsafe path) transfers excluded from `state.paths`.
- Update `is_ignored` to recognize bare `.git` files at root and within subdirectories.
- Add regression tests covering hash-matched state retention and `.git` path filtering.

**Non-Goals:**
- Modifying the 3-way hash reconciliation or clock skew resolution logic.
- Changing API network protocols or server storage handling.

## Decisions

### Decision 1: Register hash-matched and resumed files into `completed_downloads`
- **Choice**: Call `completed_downloads.insert(path.clone())` before `continue;` in both the `prev_downloaded` and `local_hash == *hash` branches in the download execution loop.
- **Rationale**: An existing local file whose full SHA-256 hash matches the server's remote hash is fully synchronized. Inserting it into `completed_downloads` ensures it is restored to `state.paths` when merged with `base_synced`.
- **Alternatives considered**: Including matching files in `base_synced` during planning: Rejected because local file hashes may not be available or readable at initial scan time; the download loop provides the authoritative point of disk content verification.

### Decision 2: Match bare `.git` files in `is_ignored`
- **Choice**: Add `|| normalized == ".git" || normalized.ends_with("/.git")` to the `.git` condition in `is_ignored`.
- **Rationale**: Follows the convention already established for `.brandybox` and `.uploads`, correctly ignoring git submodule and worktree pointer files.
- **Alternatives considered**: Adding `.git` to `SYNC_IGNORE`: `SYNC_IGNORE` matches `Path::file_name()`, which would work for filenames, but keeping directory and file exclusions together in the prefix/normalized check maintains explicit consistency.

## Risks / Trade-offs

- **[Risk]** Does inserting into `completed_downloads` risk marking a failed download as successful?
  - *Mitigation*: No. Downloads that fail (network timeout, HTTP error, permission denied) route to the `Err` branch and `skipped_downloads`, leaving `completed_downloads` untouched.
