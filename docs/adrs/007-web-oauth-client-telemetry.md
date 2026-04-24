# ADR 007: Web UI, Google OAuth (admin-linked), JWT, and client telemetry

## Status

Accepted — describes intended behaviour for the Brandy Box **web SPA** and related **backend** features (2026).

## Context

Operators need **browser access** to files without installing the Tauri client. Google SSO is requested, but **users must be pre-provisioned** by an admin (no automatic account creation from Google). Desktop clients should report **version and last sync** so operators can diagnose issues. A **secondary diagnostics** surface (not primary UX) should surface errors and client status for **admins**.

## Decision

1. **Session after Google login**  
   Use the **same JWT access + refresh pair** as password login once Google identity is verified. No separate session cookie for the main API.

2. **Google OAuth — link existing users only**  
   - Server-side **authorization code** flow (client secret stays on server).  
   - After Google returns a verified **email**, look up `User` by primary key email.  
   - If **no row**: return **403** with a generic message (no auto-provision).  
   - If row exists: optionally persist `google_sub` for stable account binding; issue JWT pair.  
   - **One-time exchange**: OAuth callback redirects the browser to the SPA with an **opaque exchange id**; the SPA calls **`POST /api/auth/oauth/complete`** to receive tokens and invalidate the exchange (prevents long-lived tokens in URLs).

3. **Trust boundaries vs Cloudflare Access**  
   **Google OAuth** is the application-level identity for the web UI. **Cloudflare Access** (if enabled in front of the tunnel) is an **optional extra** network gate; this ADR does not require it. If both exist, operators must ensure they do not break OAuth redirects or fragment handling.

4. **Client ping (`POST /api/clients/ping`)**  
   Authenticated clients (Tauri, web) send **client_type**, **client_version**, optional **last_sync_at**, **last_sync_ok**. Server stores **one row per (user_email, client_type)** (upsert) with **last_seen_at** and **backend_version_at_ping** for compatibility visibility.

5. **Server events (admin diagnostics)**  
   Append-only **server_events** rows for selected API failures and optional client-reported errors. **Retention**: cap list API (e.g. last 200) and optional periodic prune by age (implementation detail). **Admin-only** read API.

6. **User preferences (server-stored JSON)**  
   Theme, background image URL, opacity, favorite paths — **per user**, for cross-device consistency on the web app.

7. **Static hosting**  
   SPA is served from the **same origin** as the API (single `HOST_PORT` on the Pi) via FastAPI `StaticFiles` + SPA fallback to avoid CORS complexity for LAN and tunnel.

## Consequences

- **Luke** owns OAuth correctness (state/CSRF, redirect allowlist), exchange TTL, and static mount order (`/api` before `/`).  
- **Vader** owns regression tests for **admin-only OAuth**, **IDOR** on preferences/events, and **token leakage** (logs, URLs).  
- **Leia** owns responsive UX; diagnostics remain **non-prominent** (footer / drawer).

## References

- OWASP OAuth 2.0 Security (redirect URI validation, state parameter).  
- Google OAuth 2.0 for web server apps (authorization code flow).
