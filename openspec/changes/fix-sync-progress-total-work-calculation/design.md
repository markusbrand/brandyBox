## Context

See `proposal.md` for motivation. In `client-tauri/src-tauri/src/sync.rs`, the synchronization engine coordinates four distinct execution phases:
1. `delete_server`
2. `delete_local`
3. `download`
4. `upload`

Previously, `total_work` was estimated before `to_download` and `to_upload` were built using only `current_remote \ current_local` and `current_local \ current_remote`. Because modified files already exist in both sets, they were excluded from the work estimate, causing progress undercounting or overflow during transfers.

## Goals / Non-Goals

**Goals:**
- Construct the transfer candidate lists (`to_download` and `to_upload`) prior to executing file operations so the complete sync plan is known.
- Set `total_work = (to_del_remote.len() + to_del_local.len() + to_download.len() + to_upload.len()) as u64`.
- Log the complete sync plan upfront before executing deletions.
- Keep progress reporting strictly bounded (`done <= total_work`) and monotonic.
- Maintain existing 3-way hash reconciliation, clock skew resilience, and deletion failure handling.

**Non-Goals:**
- Modifying UI components in `client-tauri/src/Settings.tsx` (which already render `current / total` and calculate percentage).
- Changing sync conflict resolution rules or hash algorithms.

## Decisions

### Decision 1: Compute full sync plan upfront before executing deletions
- **Rationale**: Evaluating `to_download` and `to_upload` relies only on read operations (`safe_local_path`, file hashes, and remote item listings). Deletion targets are already partitioned into `to_del_remote_set` and `to_del_local_set`, which both candidate lists filter out. Constructing them upfront provides an exact total work item count and allows logging the plan before any mutations occur.
- **Alternatives considered**:
  - Dynamically incrementing `total_work` when encountering modified files: causes the progress bar to regress or jump unexpectedly, providing a confusing user experience.

### Decision 2: Maintain delayed base_synced resolution for failed local deletions
- **Rationale**: If a local file scheduled for deletion cannot be deleted (e.g. file lock or permissions), it is added to `failed_local_deletions` and preserved in `base_synced` to prevent resurrection. We maintain this flow by calculating `base_synced` after local deletions complete.

## Risks / Trade-offs

- [Risk] File deleted or modified by another application between planning and transfer execution → Mitigation: Transfer loops already handle missing files gracefully (`safe_local_path`, `full.exists()`, and 404 response handling), recording skipped transfers and warning summaries without crashing.
