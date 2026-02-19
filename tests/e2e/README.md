# E2E tests — Brandy Box

End-to-end scenarios (sync, large file) that run the client and verify behaviour against the API.

## One-time setup: separate test user and folder

To keep **production** (e.g. your real user and `~/brandybox`) separate from **E2E**, use a dedicated E2E config. The client then uses a different config directory and keyring namespace for tests.

### 1. Repo-root `.env`

Create or edit `.env` at the **repository root** (same directory as `client/`, `backend/`, `tests/`):

- Copy from `.env.example`: `cp .env.example .env`
- Set **test** credentials (not your production account):
  - `BRANDYBOX_TEST_EMAIL=` your test user email
  - `BRANDYBOX_TEST_PASSWORD=` your test user password
- Set the E2E sync folder (must be writable; will be used by the E2E client):
  - `BRANDYBOX_SYNC_FOLDER=/absolute/path/to/brandyBox/tests/e2e/sync_test_dir`
  - Example (Linux): `BRANDYBOX_SYNC_FOLDER=/home/you/cursorProjects/brandyBox/tests/e2e/sync_test_dir`

Ensure the sync folder exists, e.g.:

```bash
mkdir -p tests/e2e/sync_test_dir
```

### 2. Create a test user on the backend

Create a second user on your Brandy Box backend (e.g. via admin UI or API) and use that email/password for `BRANDYBOX_TEST_EMAIL` and `BRANDYBOX_TEST_PASSWORD` in `.env`. Do not use your production account for E2E.

### 3. Run the client once with the E2E config

From the **repository root**, with the venv activated:

```bash
# Linux/macOS
BRANDYBOX_CONFIG_DIR="$(pwd)/tests/e2e/e2e_client_config" python -m brandybox.main
```

- A **second** Brandy Box window/tray may appear (E2E config is separate from your normal one).
- **Log in** with the **test** user (same as `BRANDYBOX_TEST_EMAIL` / `BRANDYBOX_TEST_PASSWORD`).
- In **Settings**, set the **sync folder** to the **same path** as in `.env`, e.g.  
  `/home/you/cursorProjects/brandyBox/tests/e2e/sync_test_dir`.
- Save and close the client.

Credentials and sync folder are stored in `tests/e2e/e2e_client_config/` and in the keyring under **"BrandyBox-E2E"**, so your production config and keyring ("BrandyBox") are untouched.

### 4. Run E2E

From the repo root:

```bash
python -m tests.e2e.run_autonomous_sync
# or
python -m tests.e2e.run_all_e2e
```

When `BRANDYBOX_SYNC_FOLDER` is set in `.env`, the E2E runner starts the client with `BRANDYBOX_CONFIG_DIR=tests/e2e/e2e_client_config`, so the test user and test folder are used automatically. You can leave your production client running; the E2E client runs with the separate config.

## Optional env vars

- **BRANDYBOX_E2E_CLIENT_RUNNING=1** — Do not start the client; assume it is already running (e.g. you started it manually with the E2E config).
- **BRANDYBOX_BASE_URL** — Override API base URL (default: automatic/local).
- **BRANDYBOX_E2E_MAX_ATTEMPTS** — Max retries per scenario (default 5).

## Scenarios

- **sync_e2e** — Small file and folder: create → wait for sync → verify on server → delete → verify removed.
- **large_file_sync** — One large file (default 2 MiB); same flow. Set **BRANDYBOX_LARGE_FILE_SIZE_MB** to change size.
