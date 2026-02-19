# Client troubleshooting

## System metadata files (`.directory`, `Thumbs.db`, etc.)

Files like `.directory` (KDE Dolphin), `Thumbs.db`, `Desktop.ini` (Windows), and `.DS_Store` (macOS) are created automatically by the OS or file manager to store view settings or thumbnails. **Brandy Box does not need them** for syncing your actual content.

The client **ignores** these names: they are never uploaded and never downloaded. So they no longer clutter the server or cause permission errors on other operating systems. If such a file was synced to the server in the past, it remains there but the client will not try to download it (and will not delete it from the server, so other clients can keep it if they want). The list of ignored basenames is fixed in the sync engine (see `SYNC_IGNORE_BASENAMES` in `sync/engine.py`).

## Sync: "Permission denied" when downloading another file

**Symptom:** Sync fails or logs a warning like:

```text
[ERROR] brandybox.sync.engine: Download <path>: [Errno 13] Permission denied: '...'
```

This can happen on **Windows** (e.g. work PCs without admin rights) when the client cannot write a file locally—e.g. read-only or blocked by policy.

**What the client does:** The sync engine treats such permission errors as non-fatal: it logs a **warning** and **skips** that file, and continues syncing all other files. The sync cycle completes successfully; only the affected file is not updated locally.

**What you can do:**

- **Nothing:** If you don’t need that file, ignore the warning; the rest of your data stays in sync.
- **Remove read-only (if allowed):** Right-click the file → Properties → uncheck “Read-only” → OK, then sync again.
- **Delete or rename locally:** If you don’t need the file, delete or rename it; the next sync will try again and, if still denied, skip it again.
