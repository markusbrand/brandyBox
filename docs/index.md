# Brandy Box

Sync a local folder to your Raspberry Pi storage (Dropbox-style). Backend runs in Docker on the Pi; desktop client runs on Windows, Linux, and Mac. A **browser UI** (`web/`) is bundled in the backend image and served at `/` on the same port as the API.

The browser UI's **Files** page behaves like a desktop file explorer: a hierarchical view that shows one folder level at a time, with a clickable breadcrumb path (`home / firstfolder / secondfolder / …`) and Material-Design icons per file type (image, video, audio, PDF, Office docs, text, code, archive, generic). Click a folder row to descend into it. A `..` row at the top of any sub-folder takes you back up one level. File rows show **size** and modified date. A **New folder** button creates an empty folder inside the current view, and uploads always go into the folder you're currently viewing.

These features rely on **API 0.3.0** additions which stay backward compatible:

- ``GET /api/files/list`` now includes a ``size`` field on each file row (older clients ignore it).
- ``GET /api/files/folders`` returns every directory under the user's root with ``path`` + ``mtime`` (used so the web UI can render empty folders).
- ``POST /api/files/mkdir?path=…`` creates an empty folder. Idempotent, returns 409 if a file already exists at that path. Sync clients (Tauri, legacy Python) do not need to call these new endpoints.

## Quick links

- [ADR 006 — Sync semantics & trust boundaries](adrs/006-sync-semantics-trust-boundaries.md)
- [ADR 007 — Web UI, Google OAuth (admin-linked), JWT, client telemetry](adrs/007-web-oauth-client-telemetry.md)
- [Security review checklist](security-review.md)
- [Backend overview](backend/overview.md)
- [Client overview](client/overview.md)
- [Client troubleshooting](client/troubleshooting.md)
- [Releasing](releasing.md)
- [License](license.md) — Apache 2.0
- [README](https://github.com/markusbrand/brandyBox/blob/master/README.md) in the repo for installation and run instructions.
