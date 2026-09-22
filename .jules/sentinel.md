## 2023-10-27 - Path Traversal in Chunked Uploads
**Vulnerability:** Path traversal in `/upload/chunk` and `/upload/finalize` endpoints where `upload_id` (user input) was directly appended to the path without validation.
**Learning:** The chunked upload implementation bypassed the normal file path resolution (`resolve_user_path`), which had traversal checks, and manually appended `upload_id` to `.uploads/` directory instead.
**Prevention:** Always use proper type validation for user input in FastAPI (e.g. `upload_id: uuid.UUID` instead of `str`) before passing it into file operations, especially if it creates directories.

## 2024-05-27 - Fix timing attack in login

**Vulnerability:** User enumeration via timing attack in the `/auth/login` endpoint.
**Learning:** `passlib.context.CryptContext.verify` takes significant time to execute. If it is only called when a user exists, an attacker can determine if a given email is registered based on response time.
**Prevention:** Use `pwd_context.dummy_verify()` or ensure the verify function executes regardless of whether the user exists or not.

## 2024-05-24 - [HIGH] Fix overly permissive CORS configuration
**Vulnerability:** The CORS configuration in `backend/app/main.py` allowed any header (`allow_headers=["*"]`).
**Learning:** Using `*` for CORS headers can expose the application to potential security risks, such as CSRF or cross-site information leakage, if a malicious site requests a specific sensitive header to be reflected or modified.
**Prevention:** Explicitly define the list of allowed CORS headers instead of relying on wildcards.
## 2024-05-28 - Overly Permissive CORS Configuration
**Vulnerability:** Overly permissive CORS configuration allowing all headers (`allow_headers=["*"]`).
**Learning:** The backend allowed any HTTP headers in cross-origin requests, which can lead to unexpected behavior or security issues if sensitive headers are sent or exploited.
**Prevention:** Explicitly allow only necessary headers in CORS configuration (e.g., `["Accept", "Authorization", "Content-Type", "X-E2E-Return-Temp-Password"]`) instead of using wildcards.

## 2024-05-28 - Memory Exhaustion DoS in FastAPI
**Vulnerability:** Memory Exhaustion DoS in `/users/me/background-image` caused by loading the entire request body into RAM using `await request.body()`.
**Learning:** `await request.body()` reads the full payload into memory before returning it. For potentially large uploads, this allows an attacker to exhaust server memory.
**Prevention:** Instead of `await request.body()`, stream the request using `async for chunk in request.stream():` and enforce size limits progressively.

## 2025-02-12 - [HIGH] Fix Login CSRF in Google OAuth flow
**Vulnerability:** Google OAuth flow was missing CSRF protection, allowing an attacker to log a victim into the attacker's account (Login CSRF). The `state` parameter was generated and verified against a database table, but it was not bound to the user's browser session.
**Learning:** Storing the `state` parameter only in the database and checking if it exists is insufficient for CSRF protection in OAuth. The `state` must be bound to the user's specific browser session (e.g., via an HttpOnly cookie) so that when the callback occurs, we can verify the request originated from the same browser that initiated the flow.
**Prevention:** Always bind the OAuth `state` parameter to a secure, HttpOnly, and SameSite=lax browser cookie during the start phase, and verify it matches the `state` query parameter during the callback phase.
