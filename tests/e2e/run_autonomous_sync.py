#!/usr/bin/env python3
"""
Autonomous E2E sync test: run the sync scenario, on failure run cleanup and retry until success.

Usage (from repo root):
  export BRANDYBOX_TEST_EMAIL=your@email.com
  export BRANDYBOX_TEST_PASSWORD=yourpassword
  # optional: BRANDYBOX_BASE_URL, BRANDYBOX_SYNC_FOLDER
  python -m tests.e2e.run_autonomous_sync

Or:
  python tests/e2e/run_autonomous_sync.py

Requires: client installed (pip install -e client) or PYTHONPATH=client when running.
"""

import logging
import os
import sys
from pathlib import Path

# Ensure repo root and client are on path when run as script or -m
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
_client = _repo_root / "client"
if _client.exists() and str(_client) not in sys.path:
    sys.path.insert(0, str(_client))

from tests.e2e.sync_scenario import SyncE2EScenario

log = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 5


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    max_attempts = int(os.environ.get("BRANDYBOX_E2E_MAX_ATTEMPTS", str(DEFAULT_MAX_ATTEMPTS)))
    scenario = SyncE2EScenario()
    for attempt in range(1, max_attempts + 1):
        log.info("=== Attempt %d/%d: %s ===", attempt, max_attempts, scenario.name)
        success, error = scenario.run()
        if success:
            log.info("Scenario passed on attempt %d", attempt)
            return 0
        log.warning("Scenario failed: %s", error)
        if attempt < max_attempts:
            log.info("Running cleanup and retrying...")
            scenario.cleanup()
    log.error("All %d attempts failed", max_attempts)
    return 1


if __name__ == "__main__":
    sys.exit(main())
