---
name: autonomous-testing-brandybox
description: Run and extend Brandy Box tests autonomously on the Tauri client (client-tauri): unit and E2E tests, add or extend E2E scenarios (create file, sync, verify), identify performance bottlenecks, optimize code, and produce a test summary. Use when the user asks for automatic tests, autonomous testing, extending test cases, sync E2E tests, performance testing, or test summary.
---

# Autonomous Testing for Brandy Box

Apply this skill when running tests autonomously, extending test scenarios, or producing a test summary. All testing runs on the **Tauri client (client-tauri)**; the agent executes unit and E2E tests, optionally adds new scenarios, identifies bottlenecks, suggests optimizations, and always ends with a structured summary.

## When to use

- User asks for "automatic tests", "autonomous testing", "run the tests", or "test summary"
- User wants to "extend test cases" or "add new test scenarios"
- User mentions "create file, sync, check if there", "E2E sync test", or "performance bottlenecks"

## Test layout (existing)

- **Client under test**: **client-tauri** (Tauri desktop app) only. The Python client in `client/` is not tested.
- **Unit tests**: **client-tauri** (Rust, `cd client-tauri/src-tauri && cargo test`) and **backend** (pytest, `cd backend && pytest`).
- **E2E scenarios**: `tests/e2e/` — extensible framework; the **client under test is the client-tauri** desktop app (built binary). Framework:
  - `scenario_base.py`: `BaseScenario`, `ScenarioStep`, `StepResult` — subclass to add scenarios
  - `sync_scenario.py`: `SyncE2EScenario` — starts Tauri client, create file/folder in sync dir, verify on server, delete, verify removed
  - `run_autonomous_sync.py`: runs sync scenario with retries and cleanup
  - `run_all_e2e.py`: discovers and runs all scenario classes in `tests/e2e/` (if present)
  - **Before E2E**: build the Tauri client from repo root: `cd client-tauri && npm run tauri:build` (or `cargo build --release` in src-tauri; binary at `client-tauri/src-tauri/target/release/brandybox`). Use `tauri:build` when CI=1 causes `--ci` errors.

## Autonomous run workflow

1. **Run unit tests**
   - From repo root: `cd backend && pytest` then `cd client-tauri/src-tauri && cargo test`
   - If either fails, report failures and fix or document before proceeding.

2. **Run E2E tests (client-tauri only)**
   - **Build client-tauri first**: From repo root run `cd client-tauri && npm run tauri:build` (or `cargo build --release` in src-tauri) so the E2E runner can start the Tauri binary (`client-tauri/src-tauri/target/release/brandybox` or `target/debug/brandybox`).
   - **Autonomous (recommended)**: Set `BRANDYBOX_ADMIN_EMAIL` and `BRANDYBOX_ADMIN_PASSWORD` in repo-root `.env`. The runner sends `X-E2E-Return-Temp-Password` when creating the test user so the backend returns the temp password and skips sending email (SMTP can stay configured). Creates test user and folders, **starts the client-tauri app** with E2E config, runs the scenario(s), then **cleans up**: stops the Tauri client process, deletes the test user, clears keyring and config, wipes sync folder contents. No manual login; no leftover client or test data.
   - **Legacy**: Set `BRANDYBOX_TEST_EMAIL` and `BRANDYBOX_TEST_PASSWORD` (one-time client login + sync folder setup; see tests/e2e/README.md).
   - Optional env: `BRANDYBOX_BASE_URL`, `BRANDYBOX_SYNC_FOLDER`, `BRANDYBOX_E2E_MAX_ATTEMPTS`
   - Run: `python -m tests.e2e.run_autonomous_sync` (single scenario) or `python -m tests.e2e.run_all_e2e` (all discovered scenarios)
   - On failure: cleanup runs automatically; retry up to `BRANDYBOX_E2E_MAX_ATTEMPTS` (default 5). Do not retry on 401 or "client could not start".

3. **Optionally extend test cases**
   - New scenario: create `tests/e2e/<name>_scenario.py`, subclass `BaseScenario`, implement `name`, `steps()` (list of `ScenarioStep`), and `cleanup()` if needed.
   - Each step: callable returning `StepResult(name, success, message="", details=None)`.
   - Register by adding the scenario class to the list in `run_all_e2e.py` (or rely on discovery if implemented).
   - Example flow: create file in sync folder → wait for sync → verify via API that file appears → delete → verify removed. Reuse helpers from `sync_scenario.py` (e.g. `_get_sync_folder()`, `_get_api_client()`, `_login_and_list()`) where useful.

4. **Identify performance bottlenecks**
   - Add timing to E2E steps (e.g. `time.monotonic()` around sync wait loops) and log or attach to `StepResult.details`.
   - Run backend unit tests with pytest timing: `cd backend && pytest --durations=10`. For client-tauri use `cargo test` (Rust test output includes timing).
   - If the user wants deeper profiling, run backend or client under a profiler (e.g. `python -m cProfile -o profile.stats`) and summarize hot paths.

5. **Optimize and re-verify**
   - After code changes for performance: re-run unit tests and E2E to ensure no regressions. Re-run only affected areas if obvious.

6. **Produce test summary**
   - Use the template in [reference.md](reference.md). Include: unit test result (pass/fail, counts), E2E result per scenario, timings or bottlenecks if collected, and any failures or optimizations made.

## Extending scenarios (agent can do this)

- **New E2E file**: Add `tests/e2e/<something>_scenario.py`. Subclass `BaseScenario`; implement `name`, `steps()`, and optionally `cleanup()`.
- **Step pattern**: Create artifacts → wait (poll API/list) → verify → delete → wait → verify removed. Use `StepResult(success=False, message="...", details={...})` for failures.
- **Discovery**: If `run_all_e2e.py` exists, it discovers `*_scenario.py` modules and runs all `BaseScenario` subclasses; otherwise add the new scenario to the runner’s list manually.
- Keep scenarios independent (cleanup so retries or other scenarios are not affected).

## Commands (from repo root)

```bash
# Unit tests — backend + client-tauri (Tauri client only)
cd backend && pytest
cd client-tauri/src-tauri && cargo test

# E2E — client-tauri only: build first, then autonomous (set BRANDYBOX_ADMIN_EMAIL, BRANDYBOX_ADMIN_PASSWORD in .env)
cd client-tauri && npm run tauri:build
python -m tests.e2e.run_autonomous_sync
# Or all scenarios:
python -m tests.e2e.run_all_e2e
```

## Feedback format

- **Critical**: Failing tests, broken E2E, auth/setup blockers.
- **Suggestion**: Slow tests, missing coverage, new scenario ideas.
- **Summary**: Always provide the test summary (see reference.md) at the end of an autonomous run.

## Additional resources

- Test summary template and performance notes: [reference.md](reference.md).
- General QA and conventions: use the `quality-assurance-brandybox` skill for checklist and security patterns.
