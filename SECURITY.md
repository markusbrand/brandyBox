# Security review

Security measures applied per the project security-review skill (OWASP/CWE–aligned).

## Checklist summary

- **Injection & input**: Backend uses parameterized SQL (SQLAlchemy ORM); file paths are sanitized (no `..`, allowlisted segments). Client subprocess calls use list arguments (no shell). No unsanitized user input in logs.
- **Auth**: All file and user endpoints require authentication (Bearer JWT). Admin-only routes use `get_current_admin`. Login/refresh are rate-limited.
- **Secrets**: No hardcoded secrets; backend uses env (`BRANDYBOX_*`). Client stores only refresh token and email in OS keyring.
- **Path / file**: Backend `files/storage.py` resolves paths under a user-scoped base; traversal and unsafe segments are rejected (CWE-22).
- **Rate limiting**: Login and refresh (slowapi); file list/upload/download limited per IP.
- **Errors**: Generic 500 handler returns `{"detail": "Internal server error"}` without stack trace or paths. Validation errors are FastAPI’s default (no internal leakage).
- **Headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` on all backend responses. CORS restricted to configured origins.
- **Dependencies**: Backend and client use pinned/lockfile-friendly dependency lists; no known vulnerable patterns in current stack.

## Recommendations

- Run the backend behind HTTPS in production (e.g. Cloudflare tunnel or reverse proxy).
- Rotate `BRANDYBOX_JWT_SECRET` if compromised; use a long random value.
- Keep dependencies updated; run `pip audit` or similar periodically.
