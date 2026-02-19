#!/usr/bin/env python3
"""
Autonomous E2E sync test: run the sync scenario, on failure run cleanup and retry until success.

Usage (from repo root):
  Set credentials via repo-root .env (recommended) or environment:
    .env at repo root: BRANDYBOX_TEST_EMAIL=... BRANDYBOX_TEST_PASSWORD=...
  Or: export BRANDYBOX_TEST_EMAIL=... BRANDYBOX_TEST_PASSWORD=...
  Optional in .env or env: BRANDYBOX_BASE_URL, BRANDYBOX_SYNC_FOLDER, BRANDYBOX_E2E_CLIENT_RUNNING=1
  python -m tests.e2e.run_autonomous_sync

Or:
  python tests/e2e/run_autonomous_sync.py

Requires: client installed (pip install -e client) or PYTHONPATH=client when running.
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

from tests.e2e.env_loader import load_e2e_env
load_e2e_env(_repo_root)

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


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    email = os.environ.get("BRANDYBOX_TEST_EMAIL", "").strip()
    password = os.environ.get("BRANDYBOX_TEST_PASSWORD", "").strip()
    if not email or not password:
        log.error("BRANDYBOX_TEST_EMAIL and BRANDYBOX_TEST_PASSWORD must be set.")
        log.error("Set them in repo-root .env (see .env.example) or in the environment.")
        log.error("PowerShell: $env:BRANDYBOX_TEST_EMAIL = \"you@example.com\"; $env:BRANDYBOX_TEST_PASSWORD = \"...\"")
        log.error("CMD: set BRANDYBOX_TEST_EMAIL=you@example.com && set BRANDYBOX_TEST_PASSWORD=...")
        return 1
    max_attempts = int(os.environ.get("BRANDYBOX_E2E_MAX_ATTEMPTS", str(DEFAULT_MAX_ATTEMPTS)))
    scenario = SyncE2EScenario()
    for attempt in range(1, max_attempts + 1):
        log.info("=== Attempt %d/%d: %s ===", attempt, max_attempts, scenario.name)
        success, error = scenario.run()
        if success:
            log.info("Scenario passed on attempt %d", attempt)
            return 0
        log.warning("Scenario failed: %s", error)
        if _is_credentials_missing(error or ""):
            log.error("Credentials not set. Use PowerShell: $env:BRANDYBOX_TEST_EMAIL = \"...\"; $env:BRANDYBOX_TEST_PASSWORD = \"...\"")
            return 1
        if _is_auth_error(error or ""):
            log.error(
                "Login failed (401). Check BRANDYBOX_TEST_EMAIL and BRANDYBOX_TEST_PASSWORD. No retry."
            )
            return 1
        if _is_client_not_started(error or ""):
            log.error(
                "Client did not start (no tray/display?). Start Brandy Box manually and re-run. No retry."
            )
            return 1
        if _is_rate_limited(error or "") and attempt < max_attempts:
            log.info("Rate limited (429). Waiting %ds before retry...", RATE_LIMIT_WAIT_SECONDS)
            time.sleep(RATE_LIMIT_WAIT_SECONDS)
        if attempt < max_attempts:
            log.info("Running cleanup and retrying...")
            scenario.cleanup()
    log.error("All %d attempts failed", max_attempts)
    return 1


if __name__ == "__main__":
    sys.exit(main())
