## 2023-10-27 - Path Traversal in Chunked Uploads
**Vulnerability:** Path traversal in `/upload/chunk` and `/upload/finalize` endpoints where `upload_id` (user input) was directly appended to the path without validation.
**Learning:** The chunked upload implementation bypassed the normal file path resolution (`resolve_user_path`), which had traversal checks, and manually appended `upload_id` to `.uploads/` directory instead.
**Prevention:** Always use proper type validation for user input in FastAPI (e.g. `upload_id: uuid.UUID` instead of `str`) before passing it into file operations, especially if it creates directories.

## 2024-05-27 - Fix timing attack in login

**Vulnerability:** User enumeration via timing attack in the `/auth/login` endpoint.
**Learning:** `passlib.context.CryptContext.verify` takes significant time to execute. If it is only called when a user exists, an attacker can determine if a given email is registered based on response time.
**Prevention:** Use `pwd_context.dummy_verify()` or ensure the verify function executes regardless of whether the user exists or not.

## 2024-05-28 - Overly Permissive CORS Configuration
**Vulnerability:** Overly permissive CORS configuration allowing all headers (`allow_headers=["*"]`).
**Learning:** The backend allowed any HTTP headers in cross-origin requests, which can lead to unexpected behavior or security issues if sensitive headers are sent or exploited.
**Prevention:** Explicitly allow only necessary headers in CORS configuration (e.g., `["Accept", "Authorization", "Content-Type", "X-E2E-Return-Temp-Password"]`) instead of using wildcards.
