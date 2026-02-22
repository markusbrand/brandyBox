"""E2E scenario: create file and folder in sync dir, verify on server, delete, verify removed."""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from tests.e2e.scenario_base import BaseScenario, ScenarioStep, StepResult

log = logging.getLogger(__name__)

# Test artifact names (folder is represented by a file inside it for server listing)
AUTOTEST_FILE = "autotest.txt"
AUTOTEST_FOLDER = "autotest"
AUTOTEST_FOLDER_FILE = f"{AUTOTEST_FOLDER}/placeholder.txt"

SYNC_POLL_INTERVAL = 15
SYNC_WAIT_TIMEOUT = 180
CLIENT_START_TIMEOUT = 30


def _repo_root() -> Path:
    """Repo root (parent of tests/)."""
    return Path(__file__).resolve().parent.parent.parent


def _client_running() -> bool:
    """True if Brandy Box client process is running."""
    try:
        if sys.platform == "win32":
            # tasklist does not show command line; use PowerShell to get CommandLine
            ps = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" -ErrorAction SilentlyContinue | ForEach-Object { $_.CommandLine }",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            stdout = (ps.stdout or "").lower()
            return "brandybox.main" in stdout or "-m brandybox" in stdout
        out = subprocess.run(
            ["pgrep", "-f", "brandybox.main"],
            capture_output=True,
            timeout=5,
        )
        return out.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _e2e_config_dir() -> Path:
    """Directory for E2E client config (test user + test sync folder). Gitignored."""
    return _repo_root() / "tests" / "e2e" / "e2e_client_config"


def _start_client() -> bool:
    """Start Brandy Box client from repo root. Returns True if started or already running.
    When using E2E config (BRANDYBOX_SYNC_FOLDER set), starts client with BRANDYBOX_CONFIG_DIR
    so it uses the test user and test folder; does not skip start just because another client is running."""
    # Allow skipping start when client is run manually (e.g. BRANDYBOX_E2E_CLIENT_RUNNING=1)
    if os.environ.get("BRANDYBOX_E2E_CLIENT_RUNNING", "").strip().lower() in ("1", "true", "yes"):
        log.info("BRANDYBOX_E2E_CLIENT_RUNNING set; assuming client is already running")
        return True
    root = _repo_root()
    e2e_config = _e2e_config_dir()
    use_e2e_config = bool(os.environ.get("BRANDYBOX_SYNC_FOLDER", "").strip())
    if not use_e2e_config and _client_running():
        log.info("Client already running")
        return True
    env = os.environ.copy()
    if use_e2e_config:
        env["BRANDYBOX_CONFIG_DIR"] = str(e2e_config)
        log.info("Starting client with E2E config dir: %s", e2e_config)
    # Ensure we can import brandybox when client is started from repo
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = str(root / "client") + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = str(root / "client")
    try:
        subprocess.Popen(
            [sys.executable, "-m", "brandybox.main"],
            cwd=root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        # Give process time to start
        for _ in range(CLIENT_START_TIMEOUT):
            time.sleep(1)
            if _client_running():
                log.info("Client started")
                return True
        log.warning("Client start timeout")
        return False
    except Exception as e:
        log.exception("Failed to start client: %s", e)
        return False


def _get_sync_folder() -> Path:
    """Sync folder: BRANDYBOX_SYNC_FOLDER env or client configured path (same as running app)."""
    folder = os.environ.get("BRANDYBOX_SYNC_FOLDER", "").strip()
    if folder:
        return Path(folder).resolve()
    try:
        from brandybox.config import get_sync_folder_path
        return get_sync_folder_path()
    except Exception:
        return Path.home() / "brandyBox"


def _get_api_client():
    """Lazy import to avoid requiring brandybox when only running scenario structure checks."""
    from brandybox.api.client import BrandyBoxAPI
    from brandybox.network import get_base_url
    base_url = os.environ.get("BRANDYBOX_BASE_URL", "").strip() or None
    return BrandyBoxAPI(base_url=base_url)


def _login_and_list(api) -> Tuple[Optional[str], Optional[list]]:
    """Login with test credentials and return (error_message, list_of_files)."""
    email = os.environ.get("BRANDYBOX_TEST_EMAIL", "").strip()
    password = os.environ.get("BRANDYBOX_TEST_PASSWORD", "").strip()
    if not email or not password:
        return "BRANDYBOX_TEST_EMAIL and BRANDYBOX_TEST_PASSWORD must be set", None
    try:
        api.login(email, password)
        files = api.list_files()
        return None, files
    except Exception as e:
        return str(e), None


class SyncE2EScenario(BaseScenario):
    """
    Scenario: create autotest.txt and autotest/placeholder.txt locally,
    wait for sync, verify on server, delete locally, wait for sync, verify removed on server.
    """

    def __init__(self) -> None:
        super().__init__(max_step_duration_seconds=SYNC_WAIT_TIMEOUT)
        self._sync_folder = _get_sync_folder()
        self._api = _get_api_client()
        self._test_file_path = self._sync_folder / AUTOTEST_FILE
        self._test_folder_path = self._sync_folder / AUTOTEST_FOLDER
        self._test_folder_file_path = self._sync_folder / AUTOTEST_FOLDER_FILE
        self._had_successful_login = False

    @property
    def name(self) -> str:
        return "sync_e2e"

    def _step1_start_client(self) -> StepResult:
        if not _start_client():
            return StepResult("start_client", False, "Could not start or detect client")
        return StepResult("start_client", True)

    def _step2_create_test_artifacts(self) -> StepResult:
        try:
            self._sync_folder.mkdir(parents=True, exist_ok=True)
            self._test_file_path.write_text("autotest file content\n", encoding="utf-8")
            self._test_folder_path.mkdir(parents=True, exist_ok=True)
            self._test_folder_file_path.write_text("placeholder\n", encoding="utf-8")
        except Exception as e:
            return StepResult("create_artifacts", False, str(e))
        return StepResult("create_artifacts", True)

    def _step3_wait_sync_after_create(self) -> StepResult:
        err, files = _login_and_list(self._api)
        if err:
            return StepResult("wait_sync_create", False, err)
        self._had_successful_login = True
        deadline = time.monotonic() + SYNC_WAIT_TIMEOUT
        last_paths = set()
        while time.monotonic() < deadline:
            _, files = _login_and_list(self._api)
            if files is not None:
                last_paths = {f["path"] for f in files}
                if AUTOTEST_FILE in last_paths and AUTOTEST_FOLDER_FILE in last_paths:
                    return StepResult("wait_sync_create", True)
            time.sleep(SYNC_POLL_INTERVAL)
        hint = (
            "E2E client may not be syncing. With autonomous setup (BRANDYBOX_ADMIN_*) config and "
            "keyring are set automatically. With legacy (BRANDYBOX_TEST_*), run the client once "
            "with BRANDYBOX_CONFIG_DIR and set sync folder to BRANDYBOX_SYNC_FOLDER. See tests/e2e/README.md."
        )
        return StepResult(
            "wait_sync_create",
            False,
            f"Timeout waiting for {AUTOTEST_FILE} and {AUTOTEST_FOLDER_FILE} on server. {hint}",
            details={"paths_seen": list(last_paths)},
        )

    def _step4_verify_server_has_artifacts(self) -> StepResult:
        err, files = _login_and_list(self._api)
        if err:
            return StepResult("verify_after_create", False, err)
        paths = {f["path"] for f in files}
        if AUTOTEST_FILE not in paths:
            return StepResult("verify_after_create", False, f"Server missing {AUTOTEST_FILE}", details=paths)
        if AUTOTEST_FOLDER_FILE not in paths:
            return StepResult("verify_after_create", False, f"Server missing {AUTOTEST_FOLDER_FILE}", details=paths)
        return StepResult("verify_after_create", True)

    def _step5_delete_local_artifacts(self) -> StepResult:
        try:
            if self._test_file_path.exists():
                self._test_file_path.unlink()
            if self._test_folder_file_path.exists():
                self._test_folder_file_path.unlink()
            if self._test_folder_path.exists():
                self._test_folder_path.rmdir()
        except Exception as e:
            return StepResult("delete_local", False, str(e))
        return StepResult("delete_local", True)

    def _step6_wait_sync_after_delete(self) -> StepResult:
        err, _ = _login_and_list(self._api)
        if err:
            return StepResult("wait_sync_delete", False, err)
        deadline = time.monotonic() + SYNC_WAIT_TIMEOUT
        last_paths = set()
        while time.monotonic() < deadline:
            _, files = _login_and_list(self._api)
            if files is not None:
                last_paths = {f["path"] for f in files}
                if AUTOTEST_FILE not in last_paths and AUTOTEST_FOLDER_FILE not in last_paths:
                    return StepResult("wait_sync_delete", True)
            time.sleep(SYNC_POLL_INTERVAL)
        still = [p for p in last_paths if p in (AUTOTEST_FILE, AUTOTEST_FOLDER_FILE)]
        return StepResult(
            "wait_sync_delete",
            False,
            f"Timeout waiting for removal of {AUTOTEST_FILE} and {AUTOTEST_FOLDER_FILE} on server",
            details={"paths_still_present": still},
        )

    def _step7_verify_server_deleted(self) -> StepResult:
        err, files = _login_and_list(self._api)
        if err:
            return StepResult("verify_after_delete", False, err)
        paths = {f["path"] for f in files}
        if AUTOTEST_FILE in paths or AUTOTEST_FOLDER_FILE in paths:
            return StepResult(
                "verify_after_delete",
                False,
                "Server still has test artifacts after delete",
                details=paths,
            )
        return StepResult("verify_after_delete", True)

    def _cleanup_local_artifacts(self) -> None:
        """Remove test file and folder from sync directory."""
        try:
            if self._test_file_path.exists():
                self._test_file_path.unlink()
            if self._test_folder_file_path.exists():
                self._test_folder_file_path.unlink()
            if self._test_folder_path.exists():
                self._test_folder_path.rmdir()
        except OSError as e:
            log.warning("Cleanup local artifacts: %s", e)

    def _cleanup_remote_artifacts(self) -> None:
        """Delete test files on server via API (so next run starts clean). Skip if we never logged in (avoids extra login attempts on 401)."""
        if not self._had_successful_login:
            log.debug("Skipping remote cleanup (no successful login this run)")
            return
        err, _ = _login_and_list(self._api)
        if err:
            return
        try:
            self._api.delete_file(AUTOTEST_FILE)
        except Exception:
            pass
        try:
            self._api.delete_file(AUTOTEST_FOLDER_FILE)
        except Exception:
            pass

    def steps(self) -> List[ScenarioStep]:
        return [
            ScenarioStep("1_start_client", self._step1_start_client),
            ScenarioStep("2_create_test_file_and_folder", self._step2_create_test_artifacts),
            ScenarioStep(
                "3_wait_sync_after_create",
                self._step3_wait_sync_after_create,
                cleanup=self._cleanup_local_artifacts,
            ),
            ScenarioStep("4_verify_server_has_file_and_folder", self._step4_verify_server_has_artifacts),
            ScenarioStep("5_delete_local_file_and_folder", self._step5_delete_local_artifacts),
            ScenarioStep(
                "6_wait_sync_after_delete",
                self._step6_wait_sync_after_delete,
                cleanup=self._cleanup_remote_artifacts,
            ),
            ScenarioStep("7_verify_server_deleted", self._step7_verify_server_deleted),
        ]

    def cleanup(self) -> None:
        """Remove local and remote test artifacts so retry can succeed."""
        self._cleanup_local_artifacts()
        self._cleanup_remote_artifacts()
        super().cleanup()
