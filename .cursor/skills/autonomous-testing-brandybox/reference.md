# Autonomous Testing Reference — Brandy Box

## Test summary template

Use this structure at the end of an autonomous test run:

```markdown
# Test Summary — [date/time or run id]

## Unit tests
- **Backend**: pass/fail — X passed, Y failed, Z skipped (duration)
- **Client-tauri**: pass/fail — X passed, Y failed (from `cargo test` in client-tauri/src-tauri)
- **Failures**: [list any failed test names and short error]

## E2E scenarios
- **sync_e2e**: pass/fail (attempt N/M, duration)
- **[other scenarios]**: pass/fail
- **Failures**: [step name and error if any]

## Performance / bottlenecks
- [Any slow tests from pytest --durations=10]
- [E2E step timings or sync wait times if collected]
- [Profiler hot paths if run]

## Optimizations applied
- [List code or config changes made for performance]

## Next steps (optional)
- [Suggested new scenarios, flaky test follow-ups, or env fixes]
```

## Adding a new E2E scenario (steps)

1. Create `tests/e2e/<name>_scenario.py`.
2. Import: `from tests.e2e.scenario_base import BaseScenario, ScenarioStep, StepResult`.
3. Subclass `BaseScenario`, set `name` (property) and implement `steps()` returning a list of `ScenarioStep(name, run_callable, cleanup=None)`.
4. Each step’s callable returns `StepResult(step_name, success, message="", details=None)`.
5. Implement `cleanup()` to remove local/remote artifacts so retries and other scenarios stay clean.
6. If using `run_all_e2e.py`: ensure the module is under `tests/e2e/` and the class is a subclass of `BaseScenario` (discovery will pick it up). Otherwise add the scenario class to the runner’s list.

## E2E environment

- **.env file for E2E**: E2E runners load variables from a **`.env` file at the repository root** (the directory that contains `client/`, `backend/`, `tests/`). Create it by copying `.env.example` and setting your values: `cp .env.example .env` then edit `.env`. The file is gitignored; never commit it.
- **Autonomous (recommended)**: **BRANDYBOX_ADMIN_EMAIL**, **BRANDYBOX_ADMIN_PASSWORD**; runner sends X-E2E-Return-Temp-Password so backend returns temp_password and skips email (SMTP can stay configured); runner creates test user and cleans up. **Legacy**: **BRANDYBOX_TEST_EMAIL**, **BRANDYBOX_TEST_PASSWORD** (one-time client setup). Set them in repo-root `.env` or in the environment. If unset, the runner exits immediately with a hint. **PowerShell**: `$env:BRANDYBOX_TEST_EMAIL = "you@example.com"; $env:BRANDYBOX_TEST_PASSWORD = "..."`
- **BRANDYBOX_E2E_CLIENT_RUNNING**: Set to `1` (or `true`/`yes`) to skip starting the client; assume it is already running (e.g. started manually or in tray). Use when client start fails or you run client separately.
- **BRANDYBOX_BASE_URL**, **BRANDYBOX_SYNC_FOLDER**, **BRANDYBOX_E2E_MAX_ATTEMPTS**: Optional (in `.env` or env). **BRANDYBOX_SYNC_FOLDER** must be a path the test process can write to and should match the folder the Brandy Box client is syncing (e.g. repo `tests/e2e/sync_test_dir`; create with `mkdir -p` and set in `.env`). **BRANDYBOX_LARGE_FILE_SIZE_MB**: For large-file scenario (default 2).

**Separate test user and folder (no production mix):** Use a dedicated E2E config so the client-tauri app runs with the test user and test sync folder only. One-time setup (legacy): run the client-tauri app once with `BRANDYBOX_CONFIG_DIR` set to the repo’s `tests/e2e/e2e_client_config` directory, log in with **BRANDYBOX_TEST_EMAIL** / **BRANDYBOX_TEST_PASSWORD**, and set the sync folder to the same path as **BRANDYBOX_SYNC_FOLDER** (e.g. `tests/e2e/sync_test_dir`). The E2E runners then start the client-tauri binary with that config dir automatically when **BRANDYBOX_SYNC_FOLDER** is set. Production stays in the default config (e.g. `~/.config/brandybox`) and keyring ("BrandyBox"); E2E uses `tests/e2e/e2e_client_config` and keyring ("BrandyBox-E2E"). See `tests/e2e/README.md` for step-by-step setup. Build the Tauri client before E2E: `cd client-tauri && npm run tauri build`.

## E2E scenarios (included)

- **sync_e2e** (`sync_scenario.py`): small file + folder, sync, verify, delete, verify removed.
- **large_file_sync** (`large_file_sync_scenario.py`): one large file (default 2 MiB), sync, verify, delete, verify removed. Override size with `BRANDYBOX_LARGE_FILE_SIZE_MB` (e.g. 5 or 10). Records create and sync-wait timings in step details for performance summary.

## Performance checks

- **Unit**: `pytest --durations=10` in `backend/` for slow tests; client-tauri uses `cargo test` (Rust output includes timing).
- **E2E**: Add timing in scenario steps; store in `StepResult(..., details={"duration_seconds": ...})` and surface in logs or summary. E2E runs the **client-tauri** app.
- **Profiling**: For backend CPU hotspots, run under `python -m cProfile -o profile.stats`; for client-tauri use Rust tooling (e.g. cargo flamegraph). Summarize top functions in the test summary.
