---
name: quality-assurance-brandybox
description: Run quality checks, tests, and convention verification for the Brandy Box project. Use when the user asks for QA, code review, testing, pre-merge checks, or validation of client/backend changes.
---

# Quality Assurance for Brandy Box

Apply this skill when performing QA, code review, or validating changes in the Brandy Box codebase.

## Project layout (conventions to verify)

- **Client**: `client/brandybox/` — packages `api`, `auth`, `sync`, `ui`. No global mutable state.
- **Backend**: `backend/app/` — `auth`, `users`, `files`, `db`. No global mutable state.
- **Tests**: Client tests under `client/tests/` (pytest). Backend tests under `backend/tests/` (pytest).

## QA checklist

Use this checklist when reviewing or validating code:

- [ ] **Layout**: New code lives in the correct package (`client/brandybox/*` or `backend/app/*`); no global mutable state.
- [ ] **OOP**: Cohesive behavior in classes (e.g. SyncEngine, BrandyBoxAPI, CredentialsStore); type hints and docstrings (Google or NumPy style) on public modules, classes, and key functions.
- [ ] **Correctness**: Logic is correct; edge cases and errors (e.g. path traversal, missing files) are handled.
- [ ] **Security**: No obvious vulnerabilities (path traversal, injection, sensitive data exposure); auth and storage paths validated.
- [ ] **Tests**: New or changed behavior has tests; existing tests still pass.
- [ ] **Docs**: If client or backend code changed, docs are updated; run `mkdocs build` from repo root (output in `site/`).

## Commands (run from repo root)

**Client tests:**
```bash
cd client && pytest
```

**Backend tests:**
```bash
cd backend && pytest
```

**Documentation:**
```bash
mkdocs build
# or: mkdocs serve
```

## Feedback format

When giving QA or code review feedback, use:

- **Critical**: Must fix before merge (bugs, security, broken tests).
- **Suggestion**: Should fix for consistency or maintainability (style, missing types/docs).
- **Nice to have**: Optional improvement.

## Git note

When suggesting commits: type the commit message in the Message field before clicking Commit, or use `git commit -m "message"` in the terminal to avoid the Source Control UI hanging.

## Additional resources

- For security checks and test patterns, see [reference.md](reference.md).
