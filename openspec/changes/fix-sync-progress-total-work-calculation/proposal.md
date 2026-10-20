## Why

During desktop client synchronization, `total_work` was pre-calculated using path set differences (`current_remote \ current_local` and `current_local \ current_remote`), which only accounts for newly added files and completely ignores modified existing files that need to be downloaded or uploaded. Consequently, whenever existing files are modified, `total_work` is undercounted (or evaluates to 0 when only existing files change), resulting in suppressed progress bars, division errors, and `done` exceeding `total_work` (reporting over 100% progress like "upload 3 / 1").

## What Changes

- Calculate the complete sync transfer sets (`to_download` and `to_upload`) prior to executing sync operations.
- Accurately determine `total_work` as `(to_del_remote.len() + to_del_local.len() + to_download.len() + to_upload.len()) as u64`.
- Log the complete sync plan upfront before any destructive or mutating operations begin.
- Ensure monotonic, bounded progress reporting (`done <= total_work`) during all sync phases.
- Add unit tests verifying `total_work` accuracy when modified existing files are present.

## Capabilities

### New Capabilities

<!-- None -->

### Modified Capabilities

- `desktop-client`: Adds a requirement for accurate synchronization progress accounting so that transfers of modified files are included in total progress and progress counts never exceed the total planned items.

## Impact

- `client-tauri/src-tauri/src/sync.rs`: Sync planning order and progress calculations.
- Desktop UI (`Settings.tsx`): Receives accurate `current` and `total` progress events across deletions, downloads, and uploads.
