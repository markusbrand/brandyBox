# Brandy Box

Sync a local folder to your Raspberry Pi storage (Dropbox-style). Backend runs in Docker on the Pi; desktop client runs on Windows, Linux, and Mac. A **browser UI** (`web/`) is bundled in the backend image and served at `/` on the same port as the API.

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
