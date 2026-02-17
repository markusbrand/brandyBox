# E2E autonomous sync test

End-to-end test that runs fully autonomously and retries (with cleanup) until the scenario passes.

## Scenario (extensible)

1. Start the Brandy Box client from the repo (if not already running).
2. Create a test file `autotest.txt` and a test folder `autotest/` with `autotest/placeholder.txt` in the configured sync folder.
3. Wait until sync succeeds (poll server list until both paths appear; optional: verify client logs).
4. Check on the server (via API) that the file and folder file are present.
5. Delete the test file and test folder on the client.
6. Wait until sync succeeds.
7. Check on the server that both have been removed.

On any failure, the runner runs cleanup (remove local and remote test artifacts) and re-runs the full scenario, up to `BRANDYBOX_E2E_MAX_ATTEMPTS` (default 5).

## Requirements

- Backend running and reachable (e.g. Raspberry Pi or local Docker).
- Test user credentials: set `BRANDYBOX_TEST_EMAIL` and `BRANDYBOX_TEST_PASSWORD`.
- Client sync folder configured (or default `~/brandyBox`). Optional: `BRANDYBOX_SYNC_FOLDER` to override.
- Optional: `BRANDYBOX_BASE_URL` if not using default (LAN or Cloudflare URL).
- From repo root: `pip install -e client` (or set `PYTHONPATH=client`).

## Run

From repo root:

```bash
export BRANDYBOX_TEST_EMAIL=your@email.com
export BRANDYBOX_TEST_PASSWORD=yourpassword
python -m tests.e2e.run_autonomous_sync
```

Or:

```bash
python tests/e2e/run_autonomous_sync.py
```

Exit code 0 on success, 1 after all retries failed.

## Extending the scenario

- Add steps in `sync_scenario.py` by appending to `steps()` and implementing step run (and optional cleanup).
- Reuse `tests/e2e/scenario_base.py`: implement a new `BaseScenario` subclass with `name`, `steps()`, and `cleanup()` for a different E2E flow, then run it from a small runner similar to `run_autonomous_sync.py`.
