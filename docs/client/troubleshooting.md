# Client troubleshooting

## Sync keeps re-downloading thousands of files after it "completed"

**Symptom:** Sync finishes, but on the next run (or after a short wait) it starts downloading again (e.g. "Downloading: 1125 / 14967 files") as if the files weren’t there.

**Likely cause:** **Wrong sync folder** – on Linux, paths are case-sensitive. If your real files are in e.g. `/home/you/brandybox` (lowercase) but Settings has `/home/you/brandyBox` (capital B), the client uses the wrong folder. It only sees the few files in that folder and treats all server files as missing, so it re-downloads them every time.

**Fix:** In Brandy Box **Settings**, open the sync folder setting and choose the folder where your synced files actually are (same path and **exact same spelling**, including capital/lowercase letters). Then run sync again. After that, the client will see the existing files and won’t re-download everything.

## "Brandy Box is already running" but I don't see the tray icon

**Symptom:** You get a popup saying Brandy Box is already running, but there is no system tray icon (or it disappeared).

**What to do:**

1. **Quit from the application menu**  
   Open your app launcher (e.g. KDE application menu), search for **"Quit Brandy Box"**, and run it. Then start **Brandy Box** again from the menu.
2. **Or quit from a terminal**  
   Run:  
   `pkill -f brandybox.main`  
   Then start Brandy Box again.

After that, the tray icon should appear when you start Brandy Box. If the tray still doesn’t show, see [Linux: tray shows square icon / no context menu](#linux-tray-shows-square-icon-no-context-menu-recurring-with-new-installs).

## Linux: tray shows square icon / no context menu (recurring with new installs)

**Symptom:** On Linux (e.g. Garuda, KDE) the tray icon appears as a **square** instead of the Brandy Box “B” icon, **right-click does not open a context menu** (or a circle/indicator appears), and sometimes a settings popup stays on screen.

**Cause:** This happens when the app cannot use the system PyGObject (AppIndicator), so it falls back to the XOrg tray backend. Common cases: (1) the **standalone PyInstaller binary** (e.g. from `~/.local/share/brandybox/BrandyBox`); (2) a **venv created without `--system-site-packages`** (the venv then cannot see the system `gi` module). This is a **known, recurring issue** with new client installs on Linux.

**Open Settings without the tray menu:** From repo root run `./scripts/run-settings-only.sh` or `python -m brandybox.main --settings` (with the project venv activated). You can also use the **Brandy Box Settings** desktop entry if it was installed with the venv script.

**Fix tray (correct icon + right-click menu) — use a venv with system site-packages:**

1. **Prerequisites** (Arch/Garuda):  
   `sudo pacman -S python-gobject libappindicator-gtk3`
2. From the **repo root**, recreate the venv with system site-packages (if you already have a `.venv` that was created without it, remove it first: `rm -rf .venv`):  
   `python -m venv .venv --system-site-packages`  
   `source .venv/bin/activate`  
   `cd client && pip install -e . && cd ..`
3. Install desktop entries that run the venv:  
   `./scripts/install_desktop_venv.sh`  
   or  
   `./assets/installers/linux_install.sh --venv`
4. Start **Brandy Box** from the application menu (the entry will now use `python -m brandybox.main` from the venv). The tray will show the correct icon and right-click menu.

See also the main [README](https://github.com/markusbrand/brandyBox/blob/master/README.md) section “Install on Linux” and [Installers](https://github.com/markusbrand/brandyBox/blob/master/assets/installers/README_installers.md) (Option A — Venv).

## System metadata files (`.directory`, `Thumbs.db`, etc.)

Files like `.directory` (KDE Dolphin), `Thumbs.db`, `Desktop.ini` (Windows), and `.DS_Store` (macOS) are created automatically by the OS or file manager to store view settings or thumbnails. **Brandy Box does not need them** for syncing your actual content.

The client **ignores** these names: they are never uploaded and never downloaded. So they no longer clutter the server or cause permission errors on other operating systems. If such a file was synced to the server in the past, it remains there but the client will not try to download it (and will not delete it from the server, so other clients can keep it if they want). The list of ignored basenames is fixed in the sync engine (see `SYNC_IGNORE_BASENAMES` in `sync/engine.py`).

## Sync engine robustness (v2)

The sync engine follows these principles to avoid discrepancies between server and client:

- **Verified state only**: A path is marked "in sync" only when we have verified it exists on both sides with matching content. Paths we failed or skipped to download/upload are never added to sync state.
- **Content hash preferred**: When the server sends content hashes, we use them to decide if upload/download is needed. This avoids spurious transfers from clock skew.
- **Skipped operations**: Download skips (e.g. 404, permission denied) and upload skips (file removed during sync) are logged and excluded from sync state. The tray icon turns **yellow** when any downloads or uploads were skipped.

If you see persistent discrepancies, change the sync folder in Settings (which clears the folder and sync state) or manually delete `~/.config/brandybox/sync_state.json`, then run sync again. This treats the server as source of truth and re-downloads everything.

## Tray icon is yellow after sync

**Symptom:** The Brandy Box tray icon turns **yellow** (instead of blue) after a sync cycle completes.

**Meaning:** The sync completed, but some **downloads** or **uploads** were skipped. This typically happens when:

**Uploads skipped:** Another process deletes or moves files in the sync folder during sync, or you manually delete/move files while sync is in progress.

**Downloads skipped:** Permission denied when writing locally (read-only folder), or file no longer on server (404).

**What the client does:** A warning is logged. The tray icon stays **yellow** and the tooltip shows the message (e.g. "5 download(s) skipped" or "3 upload(s) skipped"). Skipped paths are not marked as synced, so they will be retried on the next run.

**What you can do:** If the files were intentionally removed, nothing. If you need them synced, keep the files in place and run **Sync now** from the tray menu.

## Sync says complete but files are missing locally (Tauri client)

**Symptom:** You click "Sync now" on the Tauri client, it reports sync complete (blue or yellow icon), but comparing server files with your local sync folder shows many files missing locally.

**Possible causes and fixes:**

1. **Wrong sync folder:** On Linux, paths are case-sensitive. If Settings shows `/home/you/brandyBox` but you're comparing with `/home/you/brandybox`, the synced files are in the folder configured in Settings. Check **Settings → Sync folder** and open that folder to verify.

2. **Downloads skipped (permission denied):** If the tray icon is **yellow** after sync, hover it — you may see "X download(s) skipped (permission denied or file gone on server)". Fix write permissions on the sync folder and any subfolders, then run **Sync now** again.

3. **Stale sync state:** If you changed the sync folder, migrated from Python to Tauri, or suspect corrupted state: In Settings, change the sync folder (or re-select the same one and confirm the warning). This clears sync state; the next sync downloads everything from the server.

4. **View sync logs (dev build):** Run from terminal to see sync details: `cd client-tauri && npm run tauri dev`. Look for "Sync plan: X to_download" and "Sync cycle complete: Y downloaded, Z skipped" in the output.

## Large files (MP4, video) not syncing – tray icon blue

**Symptom:** A large file (e.g. big MP4) in your sync folder never appears on the server, but the tray icon stays **blue** (no error).

**Possible causes:**

1. **Out of memory:** The client loads the entire file into memory for upload. Very large files (e.g. 2 GB+) can cause `MemoryError`. When that happens, the sync **fails** and the tray icon turns **red** with an error message. If the icon stays blue, the upload may not have been attempted yet (sync is still processing many other files) or the file might be in a subfolder that hasn’t been reached.
2. **File removed during sync:** If the file was deleted or moved while sync ran, it would be skipped and the tray would turn **yellow** (see above).
3. **Timeout or quota:** Very large uploads can hit timeouts or hit your storage quota. Those failures produce a **red** icon and an error in the log.

**What you can do:**

- **Check the log:** Look in `~/.config/brandybox/brandybox.log` for errors mentioning the file path (e.g. "out of memory", "timeout", "507").
- **Exclude large files:** If you regularly sync very large videos, consider moving them outside the sync folder or adding support for size-based exclusions in the client.
- **Run "Sync now":** Ensure sync has finished; large syncs with many files can take a long time.

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
