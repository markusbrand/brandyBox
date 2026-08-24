#!/usr/bin/env python3
"""
Autonomous E2E sync test: create test user and folders, run sync scenario, cleanup.

Usage (from repo root) — autonomous (no manual login):
  Set admin credentials so the runner can create a test user and cleanup after:
    .env: BRANDYBOX_ADMIN_EMAIL=... BRANDYBOX_ADMIN_PASSWORD=...
  Optional: BRANDYBOX_BASE_URL, BRANDYBOX_SYNC_FOLDER.
  python -m tests.e2e.run_autonomous_sync

Legacy (manual test user): set BRANDYBOX_TEST_EMAIL and BRANDYBOX_TEST_PASSWORD
  and run once with E2E config + sync folder (see tests/e2e/README.md).
"""

import logging
import os
import sys
import time
from pathlib import Path

# Ensure repo root and client are on path when run as script or -m
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
_client = _repo_root / "client"
if _client.exists() and str(_client) not in sys.path:
    sys.path.insert(0, str(_client))

# CI has no keyring backend; set before any keyring import (e.g. from brandybox or e2e_setup).
if os.environ.get("CI") == "true":
    os.environ.setdefault("KEYRING_BACKEND", "keyrings.alt.file.PlaintextKeyring")

from tests.e2e.env_loader import load_e2e_env
load_e2e_env(_repo_root)

from tests.e2e.scenario_base import BaseScenario
from tests.e2e.sync_scenario import SyncE2EScenario

log = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 5
RATE_LIMIT_WAIT_SECONDS = 60


def _is_auth_error(error: str) -> bool:
    """True if failure is due to bad credentials (no point retrying)."""
    if not error:
        return False
    err = error.lower()
    return "401" in err or "unauthorized" in err


def _is_rate_limited(error: str) -> bool:
    """True if failure is due to rate limiting (wait and retry may help)."""
    if not error:
        return False
    return "429" in error or "too many requests" in error.lower()


def _is_client_not_started(error: str) -> bool:
    """True if failure is because the client could not be started (no point retrying)."""
    if not error:
        return False
    return "could not start" in error.lower() or "client start timeout" in error.lower()


def _is_credentials_missing(error: str) -> bool:
    """True if failure is due to missing test credentials (no point retrying)."""
    if not error:
        return False
    return "BRANDYBOX_TEST_EMAIL" in error and "BRANDYBOX_TEST_PASSWORD" in error


def _get_base_url() -> str:
    base = os.environ.get("BRANDYBOX_BASE_URL", "").strip()
    if base:
        return base.rstrip("/")
    # Default for local testing if not set
    return "http://localhost:8081"


def _run_scenario_with_retries(
    scenario: BaseScenario,
    max_attempts: int,
) -> tuple[bool, str | None]:
    """Run a scenario up to max_attempts times with retries and rate limit handling."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        log.info("=== Attempt %d/%d: %s ===", attempt, max_attempts, scenario.name)
        success, error = scenario.run()
        last_error = error
        if success:
            log.info("Scenario passed on attempt %d", attempt)
            return True, None

        log.warning("Scenario failed: %s", error)
        if _is_credentials_missing(error or ""):
            log.error("Credentials not set. See tests/e2e/README.md")
            return False, error
        if _is_auth_error(error or ""):
            log.error("Login failed (401). Check test credentials. No retry.")
            return False, error
        if _is_client_not_started(error or ""):
            log.error("Client did not start. No retry.")
            return False, error

        if _is_rate_limited(error or "") and attempt < max_attempts:
            time.sleep(RATE_LIMIT_WAIT_SECONDS)
        if attempt < max_attempts:
            scenario.cleanup()

    return False, last_error or f"All {max_attempts} attempts failed"


def _run_autonomous_mode(
    admin_email: str,
    admin_password: str,
    max_attempts: int,
) -> int:
    """Run E2E test using autonomous test user creation and cleanup."""
    from tests.e2e.e2e_setup import run_with_autonomous_setup

    sync_folder_env = os.environ.get("BRANDYBOX_SYNC_FOLDER", "").strip()
    sync_folder = Path(sync_folder_env).resolve() if sync_folder_env else None
    base_url = _get_base_url()

    def scenario_runner() -> tuple[bool, str | None]:
        scenario = SyncE2EScenario()
        return _run_scenario_with_retries(scenario, max_attempts)

    success, error = run_with_autonomous_setup(
        admin_email,
        admin_password,
        base_url,
        sync_folder=sync_folder,
        scenario_runner=scenario_runner,
    )
    if success:
        return 0
    log.error("Scenario failed: %s", error)
    return 1


def _run_legacy_mode(max_attempts: int) -> int:
    """Run E2E test using existing manual test user credentials in env."""
    scenario = SyncE2EScenario()
    success, error = _run_scenario_with_retries(scenario, max_attempts)
    if success:
        return 0
    log.error("Scenario failed: %s", error)
    return 1


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    admin_email = os.environ.get("BRANDYBOX_ADMIN_EMAIL", "").strip()
    admin_password = os.environ.get("BRANDYBOX_ADMIN_PASSWORD", "").strip()
    test_email = os.environ.get("BRANDYBOX_TEST_EMAIL", "").strip()
    test_password = os.environ.get("BRANDYBOX_TEST_PASSWORD", "").strip()
    max_attempts = int(os.environ.get("BRANDYBOX_E2E_MAX_ATTEMPTS", str(DEFAULT_MAX_ATTEMPTS)))

    if admin_email and admin_password:
        return _run_autonomous_mode(admin_email, admin_password, max_attempts)

    if test_email and test_password:
        return _run_legacy_mode(max_attempts)

    log.error(
        "Set either (autonomous) BRANDYBOX_ADMIN_EMAIL and BRANDYBOX_ADMIN_PASSWORD, "
        "or (legacy) BRANDYBOX_TEST_EMAIL and BRANDYBOX_TEST_PASSWORD. See tests/e2e/README.md"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
