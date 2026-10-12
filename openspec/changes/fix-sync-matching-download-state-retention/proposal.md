## Why

When a file scheduled in `to_download` already matches the server's content hash on local disk (`local_hash == *hash`) or was completed in a resumed cycle (`prev_downloaded`), the desktop sync engine skips transferring the payload over the network. However, because `to_download` candidates are filtered out of `base_synced` and only paths registered in `completed_downloads` are saved as synchronized, the engine omits these verified files from `state.paths` (`sync_state.json`). On subsequent sync cycles, deleting such a file locally fails to propagate a remote deletion (because `last_synced` lacks the path), causing the engine to instead treat the file as missing locally and re-download it from the server, resurrecting the deleted file. Furthermore, `is_ignored` in `sync.rs` checks only for `.git/` directory prefixes and fails to match bare `.git` files or submodule/worktree files (`.git` and `*/.git`).

## What Changes

- In `client-tauri/src-tauri/src/sync.rs`, insert `path` into `completed_downloads` when a download is skipped due to matching content hash (`local_hash == *hash`) or previous download completion (`skip && local_path.exists() && local_path.is_file()`), ensuring hash-verified files are preserved in `state.paths` (`sync_state.json`).
- In `client-tauri/src-tauri/src/sync.rs`, update `is_ignored` to ignore bare `.git` files and subdirectory submodule/worktree `.git` files (`normalized == ".git"` or `normalized.ends_with("/.git")`).
- Add regression unit tests in `sync.rs` asserting that hash-matched downloads are retained in `new_synced` and that `.git` files are ignored.

## Capabilities

### Modified Capabilities
- `desktop-client`: Require the desktop client sync engine to retain hash-verified and previously downloaded files in the persistent synchronized state (`sync_state.json`), and ignore `.git` repository and worktree files.

## Impact

- **Affected code**: `client-tauri/src-tauri/src/sync.rs`
- **APIs**: No API changes.
- **Dependencies**: No new dependencies.
- **Behavior**: Local deletions of hash-matched files propagate correctly without resurrection; git worktree / submodule `.git` files are properly ignored.
