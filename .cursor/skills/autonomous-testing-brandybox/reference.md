# Autonomous Testing Reference — Brandy Box

## Test summary template

Use this structure at the end of an autonomous test run:

```markdown
# Test Summary — [date/time or run id]

## Unit tests
- **Backend**: pass/fail — X passed, Y failed, Z skipped (duration)
- **Client**: pass/fail — X passed, Y failed, Z skipped (duration)
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

- **BRANDYBOX_TEST_EMAIL**, **BRANDYBOX_TEST_PASSWORD**: Required for API login. If unset, the runner exits immediately with a hint. **PowerShell** (not `set`): `$env:BRANDYBOX_TEST_EMAIL = "you@example.com"; $env:BRANDYBOX_TEST_PASSWORD = "..."`
- **BRANDYBOX_E2E_CLIENT_RUNNING**: Set to `1` (or `true`/`yes`) to skip starting the client; assume it is already running (e.g. started manually or in tray). Use when client start fails or you run client separately.
- **BRANDYBOX_BASE_URL**, **BRANDYBOX_SYNC_FOLDER**, **BRANDYBOX_E2E_MAX_ATTEMPTS**: Optional. **BRANDYBOX_LARGE_FILE_SIZE_MB**: For large-file scenario (default 2).

## E2E scenarios (included)

- **sync_e2e** (`sync_scenario.py`): small file + folder, sync, verify, delete, verify removed.
- **large_file_sync** (`large_file_sync_scenario.py`): one large file (default 2 MiB), sync, verify, delete, verify removed. Override size with `BRANDYBOX_LARGE_FILE_SIZE_MB` (e.g. 5 or 10). Records create and sync-wait timings in step details for performance summary.

## Performance checks

- **Unit**: `pytest --durations=10` in `backend/` and `client/` to see slow tests.
- **E2E**: Add timing in scenario steps; store in `StepResult(..., details={"duration_seconds": ...})` and surface in logs or summary.
- **Profiling**: For CPU hotspots, run the app under `python -m cProfile -o profile.stats` and inspect with `pstats` or a visualizer; summarize top functions in the test summary.
