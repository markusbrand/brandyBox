# E2E tests — Brandy Box

End-to-end scenarios (sync, large file) that run the client and verify behaviour against the API.

## Autonomous setup (recommended, no manual login)

The runner creates a **test user** and **test folder** automatically, runs the scenario(s), then **deletes the test user** and cleans up. You only need **admin** credentials.

### 1. Backend without SMTP

The backend must **not** have SMTP configured (do not set `BRANDYBOX_SMTP_HOST`). Then the admin “create user” API returns `temp_password` in the response so the E2E runner can log in as the new user and seed the keyring.

### 2. Repo-root `.env`

Create or edit `.env` at the **repository root**:

- **BRANDYBOX_ADMIN_EMAIL** — Admin user email (e.g. bootstrap admin from backend `BRANDYBOX_ADMIN_EMAIL` / `BRANDYBOX_ADMIN_INITIAL_PASSWORD`).
- **BRANDYBOX_ADMIN_PASSWORD** — Admin password.

Optional:

- **BRANDYBOX_BASE_URL** — API base URL (default: automatic/local).
- **BRANDYBOX_SYNC_FOLDER** — Sync folder path (default: `tests/e2e/sync_test_dir`).

### 3. Run E2E

From the repo root (with venv activated):

```bash
python -m tests.e2e.run_autonomous_sync
# or all scenarios
python -m tests.e2e.run_all_e2e
```

The runner will: create a unique test user via the admin API, create the E2E config dir and sync folder, seed the keyring (BrandyBox-E2E), start the client, run the scenario(s), then delete the test user and clear keyring/config. No manual login or one-time client setup.

---

## Legacy setup (manual test user)

If you prefer to use an existing test user and run the client once yourself:

1. **.env**: set **BRANDYBOX_TEST_EMAIL** and **BRANDYBOX_TEST_PASSWORD** (and optionally **BRANDYBOX_SYNC_FOLDER**).
2. Create the test user on the backend (e.g. via admin API or UI).
3. Run the client **once** with `BRANDYBOX_CONFIG_DIR="$(pwd)/tests/e2e/e2e_client_config"`, log in as the test user, and in Settings set the sync folder to the same path as **BRANDYBOX_SYNC_FOLDER** (e.g. `tests/e2e/sync_test_dir`).
4. Run `python -m tests.e2e.run_autonomous_sync` or `run_all_e2e`; the runner will use the existing credentials and config.

## Optional env vars

- **BRANDYBOX_E2E_CLIENT_RUNNING=1** — Do not start the client; assume it is already running.
- **BRANDYBOX_BASE_URL** — Override API base URL.
- **BRANDYBOX_E2E_MAX_ATTEMPTS** — Max retries per scenario (default 5).
- **BRANDYBOX_LARGE_FILE_SIZE_MB** — For large_file_sync scenario (default 2).

## Scenarios

- **sync_e2e** — Small file and folder: create → wait for sync → verify on server → delete → verify removed.
- **large_file_sync** — One large file (default 2 MiB); same flow.
