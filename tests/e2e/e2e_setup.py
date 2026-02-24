"""Autonomous E2E setup: create test user and folders, seed config/keyring, cleanup after run.

No manual login required: provide admin credentials; the runner creates a test user
via the backend admin API (backend must have SMTP unconfigured so temp_password is returned),
seeds the E2E keyring and config, runs the scenario, then deletes the test user and cleans up.
"""

import json
import logging
import os
import shutil
import signal
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

log = logging.getLogger(__name__)

E2E_CLIENT_PID_FILE = "e2e_client.pid"

# Keyring keys must match client/brandybox/auth/credentials.py
E2E_KEYRING_SERVICE = "BrandyBox-E2E"
KEY_EMAIL = "email"
KEY_REFRESH_TOKEN = "refresh_token"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _e2e_config_dir() -> Path:
    return _repo_root() / "tests" / "e2e" / "e2e_client_config"


def stop_e2e_client() -> None:
    """
    Stop the E2E Brandy Box (Tauri) client if we started it (pid in e2e_client_config/e2e_client.pid).
    Call after test run so no client instances are left running. Safe to call if file missing.
    """
    pid_path = _e2e_config_dir() / E2E_CLIENT_PID_FILE
    if not pid_path.exists():
        return
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError) as e:
        log.warning("Could not read E2E client PID from %s: %s", pid_path, e)
        try:
            pid_path.unlink(missing_ok=True)
        except OSError:
            pass
        return
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except (ProcessLookupError, OSError):
                break
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        log.info("E2E cleanup: stopped client process %s", pid)
    except ProcessLookupError:
        log.debug("E2E client process %s already gone", pid)
    except OSError as e:
        if sys.platform == "win32":
            try:
                import subprocess
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5,
                )
                log.info("E2E cleanup: sent taskkill for client PID %s", pid)
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e2:
                log.warning("E2E cleanup: could not stop client %s: %s", pid, e2)
        else:
            log.warning("E2E cleanup: could not stop client %s: %s", pid, e)
    try:
        pid_path.unlink(missing_ok=True)
    except OSError:
        pass


def _default_sync_folder() -> Path:
    """Default E2E sync folder; created if missing."""
    p = _repo_root() / "tests" / "e2e" / "sync_test_dir"
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_test_user(
    admin_email: str,
    admin_password: str,
    base_url: str,
) -> Tuple[str, str, str]:
    """
    Create a test user via admin API and return (test_email, temp_password, refresh_token).
    Sends X-E2E-Return-Temp-Password so the backend returns temp_password and skips email (SMTP not required).
    """
    from brandybox.api.client import BrandyBoxAPI

    api = BrandyBoxAPI(base_url=base_url)
    api.login(admin_email, admin_password)
    test_email = f"e2e-{uuid.uuid4().hex[:12]}@example.com"
    data = api.create_user(test_email, "E2E", "Test", e2e_return_temp_password=True)
    temp_password = data.get("temp_password")
    if not temp_password:
        raise RuntimeError(
            "Backend did not return temp_password. Ensure the backend supports the "
            "X-E2E-Return-Temp-Password header (admin create user)."
        )
    api2 = BrandyBoxAPI(base_url=base_url)
    login_data = api2.login(test_email, temp_password)
    refresh_token = login_data["refresh_token"]
    return test_email, temp_password, refresh_token


def setup_e2e_config(
    sync_folder: Path,
    test_email: str,
    refresh_token: str,
    e2e_config_dir: Optional[Path] = None,
) -> Path:
    """
    Create E2E config dir, write config.json with sync_folder, seed keyring with test user.
    Returns the config dir used.
    """
    import keyring

    config_dir = e2e_config_dir or _e2e_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps({"sync_folder": str(sync_folder.resolve())}, indent=2),
        encoding="utf-8",
    )
    keyring.set_password(E2E_KEYRING_SERVICE, KEY_EMAIL, test_email)
    keyring.set_password(E2E_KEYRING_SERVICE, KEY_REFRESH_TOKEN, refresh_token)
    log.info("E2E config ready: %s, keyring %s seeded", config_dir, E2E_KEYRING_SERVICE)
    return config_dir


def cleanup_e2e(
    test_email: str,
    admin_email: str,
    admin_password: str,
    base_url: str,
    e2e_config_dir: Optional[Path] = None,
    sync_folder: Optional[Path] = None,
    remove_sync_contents_only: bool = True,
) -> None:
    """
    Delete test user via admin API, clear E2E keyring, optionally wipe sync folder.
    If remove_sync_contents_only is True, only empty or remove test artifacts from sync_folder;
    if False and sync_folder was created by us (temp), remove the folder.
    """
    import keyring

    # Delete test user (admin API)
    try:
        from brandybox.api.client import BrandyBoxAPI

        api = BrandyBoxAPI(base_url=base_url)
        api.login(admin_email, admin_password)
        api.delete_user(test_email)
        log.info("E2E cleanup: deleted test user %s", test_email)
    except Exception as e:
        log.warning("E2E cleanup: could not delete test user %s: %s", test_email, e)

    # Clear keyring
    try:
        keyring.delete_password(E2E_KEYRING_SERVICE, KEY_EMAIL)
        keyring.delete_password(E2E_KEYRING_SERVICE, KEY_REFRESH_TOKEN)
        log.info("E2E cleanup: cleared keyring %s", E2E_KEYRING_SERVICE)
    except keyring.errors.PasswordDeleteError:
        pass
    except Exception as e:
        log.warning("E2E cleanup: keyring clear failed: %s", e)

    # Config dir: remove config and pid file so next run starts clean
    if e2e_config_dir and e2e_config_dir.exists():
        try:
            (e2e_config_dir / "config.json").unlink(missing_ok=True)
            (e2e_config_dir / E2E_CLIENT_PID_FILE).unlink(missing_ok=True)
        except OSError as e:
            log.warning("E2E cleanup: config dir cleanup failed: %s", e)

    # Sync folder: only remove contents if we want a clean slate; do not remove the dir
    if sync_folder and sync_folder.exists():
        try:
            if remove_sync_contents_only:
                for p in sync_folder.iterdir():
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        shutil.rmtree(p, ignore_errors=True)
            else:
                shutil.rmtree(sync_folder, ignore_errors=True)
        except OSError as e:
            log.warning("E2E cleanup: sync folder cleanup failed: %s", e)


def run_with_autonomous_setup(
    admin_email: str,
    admin_password: str,
    base_url: str,
    sync_folder: Optional[Path] = None,
    scenario_runner=None,
) -> Tuple[bool, Optional[str]]:
    """
    Create test user, setup config/keyring, set BRANDYBOX_TEST_* and sync folder in env,
    run scenario_runner() (e.g. a callable that runs scenario and retries), then cleanup.
    Returns (success, error_message). scenario_runner() should return (bool, Optional[str]).
    """
    sync_folder = sync_folder or _default_sync_folder()
    sync_folder.mkdir(parents=True, exist_ok=True)
    test_email = None
    try:
        test_email, temp_password, refresh_token = create_test_user(
            admin_email, admin_password, base_url
        )
        config_dir = setup_e2e_config(sync_folder, test_email, refresh_token)
        os.environ["BRANDYBOX_TEST_EMAIL"] = test_email
        os.environ["BRANDYBOX_TEST_PASSWORD"] = temp_password
        os.environ["BRANDYBOX_SYNC_FOLDER"] = str(sync_folder.resolve())
        os.environ["BRANDYBOX_CONFIG_DIR"] = str(config_dir)
        if scenario_runner:
            return scenario_runner()
        return True, None
    except Exception as e:
        log.exception("Autonomous setup failed: %s", e)
        return False, str(e)
    finally:
        stop_e2e_client()
        if test_email:
            cleanup_e2e(
                test_email,
                admin_email,
                admin_password,
                base_url,
                e2e_config_dir=_e2e_config_dir(),
                sync_folder=sync_folder,
                remove_sync_contents_only=True,
            )
        for key in (
            "BRANDYBOX_TEST_EMAIL",
            "BRANDYBOX_TEST_PASSWORD",
            "BRANDYBOX_SYNC_FOLDER",
            "BRANDYBOX_CONFIG_DIR",
        ):
            os.environ.pop(key, None)
