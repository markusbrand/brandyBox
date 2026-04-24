# C-3PO → Yoda: Industry standards & comparable systems (handoff)

**Audience:** **Yoda** (orchestrator) — distill this into **task briefs** for **Han** (architecture), **Luke** (backend + Tauri Rust), **Leia** (React UI), **R2-D2** (CI/deploy), **Vader** (QA/security).  
**Scope:** Desktop **file sync** to a **self-hosted** API (Brandy Box class: Tauri + FastAPI + Pi storage).  
**Sources:** Official docs, OWASP, and widely cited system-design material (April 2026 retrieval). **Verify** URLs and version-specific guidance before implementation.

---

## 1. Tauri v2 shell security (Luke + Han)

**Principles (industry / vendor-aligned):**

- **Deny by default:** Only grant **permissions** and **capabilities** actually required; map them to **windows/webviews** explicitly. Official: [Tauri — Security](https://v2.tauri.app/security/), [Permissions](https://v2.tauri.app/security/permissions), [Capabilities](https://v2.tauri.app/security/capabilities).
- **Least privilege:** Prefer **scoped** file system and HTTP allowances over blanket access; review whenever a new command or plugin is added.
- **CSP and web surface:** Keep **Content Security Policy** strict for the embedded UI; treat **IPC** as a trust boundary (validate inputs on Rust side). See [Tauri security overview](https://v2.tauri.app/security/).

**Yoda → Luke:** Periodic **capability audit** (`src-tauri/capabilities/`, `tauri.conf.json`) after feature work; cross-check with **`.agents/skills/tauri-v2/SKILL.md`**.

**Yoda → Han:** Decide **documented security posture** for the desktop shell (what the webview may never do, what Rust alone may do) and reflect in **`docs/adrs/`** if it changes product guarantees.

---

## 2. Sync & storage architecture (Han + Luke)

**Patterns common in “Dropbox-class” designs (educational / interview literature, not product-specific):**

- **Control plane vs data plane:** Metadata (paths, versions, ACLs) vs bytes; large systems use **chunking** and often **content-addressed** chunks for dedupe and delta sync. Useful mental model for **scaling** and **resume** even if Brandy Box stays whole-file for now. See e.g. [System design — file sync / chunking](https://crackingwalnuts.com/post/dropbox-system-design) (conceptual), [Delta sync & Merkle trees](https://www.systemdesignsandbox.com/learn/delta-sync) (conceptual).
- **Conflict handling:** Offline-first discussions stress **transparent** conflict behaviour (last-write-wins vs **conflicted copy** vs user merge). See [Sync conflict handling (offline-first)](https://dev.to/crisiscoresystems/sync-conflict-handling-in-offline-first-pwas-how-to-merge-without-lying-to-the-user-59i3).

**Yoda → Han:** Align **as-built** sync semantics (single-user folder vs multi-device conflicts) with a short **ADR** or `docs/` section so marketing and support do not over-promise.

**Yoda → Luke:** If product grows: evaluate **chunked/resumable uploads**, **etag/version** per file, and explicit **conflict filenames**; document current behaviour vs roadmap.

---

## 3. Self-hosted API & file upload security (Luke + Vader)

**OWASP-aligned baseline:**

- **File upload cheat sheet:** Allowlist extensions where practical, validate **after** decode, store **outside web root**, map **IDs → paths** internally, limit size and rate, watch **zip bombs** / decompression limits. [OWASP — File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- **Verification requirements (ASVS V12):** Path traversal, content vs extension, quotas, virus scanning where threat model demands. [OWASP ASVS V12 — Files and resources](https://github.com/OWASP/ASVS/blob/master/4.0/en/0x20-V12-Files-Resources.md)

**Operational hardening (self-hosted):**

- **TLS in transit**, reverse proxy, HSTS where HTTPS is terminated (e.g. Cloudflare tunnel). Generic checklist style: [Self-hosted file sharing foundations](https://selfhosting.sh/foundations/file-sharing-security/) (principles; adapt to Pi + tunnel).

**Yoda → Luke:** Map **`backend/app`** upload/list/download paths to ASVS-style checklist; close gaps with **tests** (path traversal, authz on other users’ prefixes).

**Yoda → Vader:** Add/extend **pytest** cases for **negative** paths (oversized file, bad path segments, cross-user access) where not already covered.

---

## 4. Comparable open ecosystems (research leads, not mandates)

Teams often study **Nextcloud**, **Seafile**, **Syncthing** (P2P), **rclone** for **CLI sync** UX and **operational** patterns—not to copy code, but for **feature parity ideas** and **operator docs** (retention, quotas, conflict policies). Yoda: ask **C-3PO** for a **focused** comparison only when product direction requires it (avoid unbounded research).

---

## 5. Prioritized backlog proposals (for Yoda to assign)

| Priority | Proposal | Owner | Status |
|----------|----------|-------|--------|
| P0 | Re-run **`./scripts/run-qa.sh`** on every release candidate; keep **`team/handoff-yoda-from-vader.md`** current. | **Vader** / **R2-D2** | Ongoing |
| P1 | **Capability + permission** review of Tauri app vs features shipped. | **Luke** (Han reviews) | **Done** — documented in **`docs/client/tauri.md`** § *Security posture*; capabilities unchanged (audited vs `lib.rs` plugins/commands). |
| P1 | **Document** sync conflict behaviour and network limits (Cloudflare body/timeouts) in user-facing docs — **`docs/network/limitations.md`** is now in **MkDocs** nav. | **C-3PO** / **Leia** (UX copy) | **Done** — **`docs/client/overview.md`**, **ADR 006**, **`docs/backend/overview.md`** (`BRANDYBOX_MAX_SINGLE_UPLOAD_BYTES`). |
| P2 | **Resumable / chunked** uploads if large files hit proxy timeouts (tie to `limitations.md`). | **Han** decision → **Luke** | **Deferred** — ADR 006 records out-of-scope; optional **`BRANDYBOX_MAX_SINGLE_UPLOAD_BYTES`** mitigates oversize at API. |
| P2 | **E2E** expansion: conflict scenario, large file, flaky network (see **`.cursor/skills/autonomous-testing-brandybox/SKILL.md`**). | **Vader** | **Partial** — **`tests/e2e/large_file_sync_scenario.py`** already exists; conflict / flaky-network scenarios still optional. |

---

## 6. Handoff checklist (Yoda)

- [ ] Read **§5** and create **one brief per row** (scope, DoD, non-goals) for the assignee.
- [ ] Attach links from **§1–3** only where relevant to that task (avoid dumping the whole doc).
- [ ] Schedule **Han** if any proposal changes **trust boundaries** or **sync contract**.
- [ ] After implementation, route **C-3PO** to update **`README.md` / `docs/`** and **Vader** to extend tests.

---

*Prepared as a research package for orchestration; not a security audit sign-off.*
