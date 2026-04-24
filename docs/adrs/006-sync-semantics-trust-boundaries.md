# ADR 006: Sync semantics, conflicts, and trust boundaries

## Status

Accepted — reflects **as-built** behaviour of Brandy Box (Tauri + FastAPI) as of 2026.

## Context

Brandy Box synchronizes a **local folder** with **per-user storage** on a self-hosted server. Comparable products use metadata servers, chunking, and explicit conflict branches; this stack uses **whole-file** transfers and **content hashes** for skip-on-unchanged downloads.

## Decision

1. **Server as source of truth after folder bind**  
   When the user confirms the sync folder, local contents can be reset; the next sync **downloads** the server tree, then **uploads** local-only files and propagates **deletes** both ways per the client sync engine.

2. **Conflict policy: last sync wins (no merge UI)**  
   Multiple devices may use the same account. If two devices change the **same file** while offline (or before sync), the version that **uploads last** replaces the server copy; other devices then **download** that version on the next cycle. There is **no** conflicted-copy filename (e.g. no `file (conflicted copy).txt`). Operators should treat this like a **single-writer** or **coordination** model for hot files.

3. **Trust boundaries**  
   - **Desktop shell (Tauri):** Rust commands and OS integrations (folder, tray, keyring) are **not** exposed to arbitrary web content; only the **bundled** frontend calls `invoke`. Capabilities follow Tauri v2 **deny-by-default** with explicit allowlists (`src-tauri/capabilities/`).  
   - **API:** JWT identifies the user; all file paths are resolved **under** `storage_base_path/<email>/` with **traversal rejected** (`resolve_user_path`).  
   - **Optional upload cap:** `BRANDYBOX_MAX_SINGLE_UPLOAD_BYTES` may be set to fail fast below reverse-proxy limits (e.g. Cloudflare body size).

4. **Resumable / chunked uploads**  
   **Out of scope** for the current contract; large uploads depend on **proxy timeouts**, **uvicorn**, and optional **`max_single_upload_bytes`**. A future ADR may introduce chunked or resumable APIs.

## Consequences

- Documentation and UX must **not** promise automatic merge or conflict branches.
- **Vader** / QA: regression tests should cover **path traversal**, **cross-user isolation**, and **413** when the upload cap is configured.
- **Luke:** Any future multi-part upload must preserve **authz** and **quota** semantics established here.

## References

- OWASP File Upload Cheat Sheet (validation, size limits).
- Tauri v2 security: permissions and capabilities (`https://v2.tauri.app/security/`).
