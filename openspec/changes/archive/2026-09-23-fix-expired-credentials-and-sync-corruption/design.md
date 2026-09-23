## Context

See `proposal.md` for motivation. The desktop client credentials store and sync engine run in background threads on macOS, Linux, and Windows. In parallel, the backend file service accepts uploads and chunked assemblies.

## Goals / Non-Goals

**Goals:**
- Eliminate infinite refresh loops caused by expired or invalid credentials in the desktop client.
- Eliminate path traversal and directory escape risks in the sync engine when mapping remote paths to local paths.
- Ensure upload endpoints never treat directory destinations as files, preventing file corruption, orphan scratch files, and invalid DB hashes.
- Enforce chunk contiguity in chunked upload assembly to prevent silent file corruption.

**Non-Goals:**
- Redesigning the entire authentication mechanism or switching from JWT to session cookies.
- Changing the chunk size or protocol of chunked uploads.

## Decisions

1. **Strict Expiration Check in `get_stored()`**:
   - *Decision*: In `credentials.rs`, evaluate `!is_jwt_expired(&token)` whenever file credentials or keyring credentials are read, including macOS and E2E configurations. Return `None` if the token is expired.
   - *Alternative Considered*: Only checking expiration in `lib.rs: get_valid_access_token()`. Rejected because other callers like `get_stored_email()` would continue reporting an active session.

2. **Purge Credentials on Refresh 401**:
   - *Decision*: When `client.refresh(&refresh_token)` returns an error containing 401 Unauthorized in `get_valid_access_token()`, call `credentials::clear_stored()`.
   - *Alternative Considered*: Retrying or ignoring. Rejected because a 401 on refresh is permanent and indicates invalid/revoked credentials.

3. **Safe Local Path Helper in `sync.rs`**:
   - *Decision*: Implement `safe_local_path(root: &Path, rel: &str) -> Option<PathBuf>` that strips leading slashes, checks for empty or `..` segments, joins with `root`, and confirms `path.starts_with(root)`. Use this helper for all delete, download, and upload path calculations.
   - *Alternative Considered*: Relying on `local_root.join(path)`. Rejected because Rust's `Path::join` replaces the base if the path begins with a slash.

4. **Directory Collision Check in Upload Endpoints**:
   - *Decision*: Check `if target.exists() and target.is_dir(): raise HTTPException(status_code=409, detail=f"A directory already exists at path: {path_param}")` in `upload_file`, `upload_init`, and `upload_finalize`.
   - *Alternative Considered*: Deleting the existing directory. Rejected because silently deleting directories leads to massive data loss.

5. **Chunk Contiguity Validation**:
   - *Decision*: In `upload_finalize`, inspect sorted chunk file names and assert that chunk `i` has name `f"chunk_{i:06d}"` for all `i` in `range(len(chunks))`. If any chunk is missing, abort with HTTP 400.
   - *Alternative Considered*: Relying on client to send expected chunk count. While good practice, validating index sequence directly from disk ensures self-consistency and rejects gaps even without client changes.

## Risks / Trade-offs

- **[Risk] Existing expired credentials file**:
  - *Mitigation*: Client will immediately return `None`, prompting login on the next UI refresh rather than looping.
- **[Risk] Sync items with unexpected leading slashes**:
  - *Mitigation*: Leading slashes are safely stripped, so normal relative paths with accidental leading slashes still resolve correctly inside the sync folder.
