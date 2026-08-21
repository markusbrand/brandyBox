## 2024-05-18 - [Enforce Fail-Secure Configuration for JWT Secrets]
**Vulnerability:** The application used an empty string `""` as a default fallback for `BRANDYBOX_JWT_SECRET` in `backend/app/config.py`.
**Learning:** Hardcoded, default, or empty fallbacks for cryptographic keys violate fail-secure principles, potentially allowing the application to silently boot up with a known, insecure secret. This can lead to arbitrary JWT token forging.
**Prevention:** Remove default fallbacks for sensitive environment variables in `pydantic` configuration settings. Always use `@field_validator` to enforce strong length constraints (e.g., minimum 32 characters for `HS256`).
