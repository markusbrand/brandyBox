# C-3PO → Yoda / Leia — Web SPA UX, OAuth, and diagnostics (2026)

## Executive summary

- **Responsive shell**: Use a **persistent collapsible nav** on desktop and a **temporary drawer** on mobile (Material / M3 patterns); keep primary actions in **app bar** with clear touch targets (**≥48dp**).
- **OAuth UX**: Primary button for password login; secondary outlined **“Continue with Google”**; explicit **error states** for `no_account` (admin must create user) without revealing whether an email exists in other flows.
- **File browsing on phone**: Prefer **virtualized or sectioned lists** by folder; **sticky path breadcrumb**; **FAB or bottom bar** for upload where appropriate; avoid horizontal-only tables.
- **Diagnostics (admin)**: Industry practice is **centralized logs** (ELK, Loki) for production; for **self-hosted small fleets**, a **read-only in-app tail** of structured events is acceptable if **admin-gated**, **non-blocking**, and **not** the default view — e.g. footer link “Diagnostics” → drawer with filters (level, time), no PII beyond what admins already see in user list.
- **Errors for end users**: Use **Snackbar** or inline **Alert** with actionable copy; map HTTP **401/403/413** to clear messages; avoid raw stack traces in UI.

## Sources (verification)

- Google Material Design 3 — Navigation drawer, touch targets (`https://m3.material.io/`).
- OWASP — OAuth 2.0 security, redirect URI validation (`https://owasp.org/www-community/attacks/OAuth2_Redirect_Uri_Manipulation`).
- Nielsen Norman — Error message guidelines (specificity, recovery).

## Open unknowns

- Exact Cloudflare tunnel path prefix (if any) must match **Google redirect URIs** registered in Google Cloud Console.

## Recommendations

1. **Single origin** for web + API on the Pi (already in ADR 007).  
2. **Preferences**: persist theme + background + favorites **server-side** so phone and desktop browser stay aligned.  
3. **QA**: test **iOS Safari** safe areas for bottom nav and drawers.
