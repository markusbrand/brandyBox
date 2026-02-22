#!/usr/bin/env python3
"""
Run all discovered E2E scenarios (BaseScenario subclasses in tests.e2e).

Usage (from repo root) — autonomous (no manual login):
  Set admin credentials: BRANDYBOX_ADMIN_EMAIL=... BRANDYBOX_ADMIN_PASSWORD=...
  Backend without SMTP so create_user returns temp_password. Optional: BRANDYBOX_BASE_URL, BRANDYBOX_SYNC_FOLDER.
  python -m tests.e2e.run_all_e2e

Legacy: set BRANDYBOX_TEST_EMAIL and BRANDYBOX_TEST_PASSWORD (see tests/e2e/README.md).

Scenarios are discovered from *_scenario.py modules (BaseScenario subclasses).
"""

import importlib.util
import logging
import os
import sys
import time
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
_client = _repo_root / "client"
if _client.exists() and str(_client) not in sys.path:
    sys.path.insert(0, str(_client))

from tests.e2e.env_loader import load_e2e_env
load_e2e_env(_repo_root)

from tests.e2e.scenario_base import BaseScenario

log = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 5
RATE_LIMIT_WAIT_SECONDS = 60


def _is_auth_error(error: str) -> bool:
    if not error:
        return False
    err = error.lower()
    return "401" in err or "unauthorized" in err


def _is_rate_limited(error: str) -> bool:
    if not error:
        return False
    return "429" in error or "too many requests" in error.lower()


def _is_client_not_started(error: str) -> bool:
    if not error:
        return False
    return "could not start" in error.lower() or "client start timeout" in error.lower()


def _is_credentials_missing(error: str) -> bool:
    """True if failure is due to missing test credentials (no point retrying)."""
    if not error:
        return False
    return "BRANDYBOX_TEST_EMAIL" in error and "BRANDYBOX_TEST_PASSWORD" in error


def _discover_scenarios() -> list[type[BaseScenario]]:
    """Load *_scenario.py modules under tests/e2e and collect BaseScenario subclasses."""
    e2e_dir = Path(__file__).resolve().parent
    scenarios: list[type[BaseScenario]] = []
    for path in sorted(e2e_dir.glob("*_scenario.py")):
        module_name = path.stem
        if module_name == "scenario_base":
            continue
        spec = importlib.util.spec_from_file_location(
            f"tests.e2e.{module_name}",
            path,
            submodule_search_locations=[str(e2e_dir)],
        )
        if spec is None or spec.loader is None:
            log.warning("Could not load spec for %s", path)
            continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            log.warning("Failed to load %s: %s", path, e)
            continue
        for attr_name in dir(mod):
            if attr_name.startswith("_"):
                continue
            obj = getattr(mod, attr_name)
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseScenario)
                and obj is not BaseScenario
            ):
                scenarios.append(obj)
    return scenarios


def _get_base_url() -> str:
    base = os.environ.get("BRANDYBOX_BASE_URL", "").strip()
    if base:
        return base.rstrip("/")
    from brandybox.network import get_base_url as _get
    return _get()


def _run_all_scenarios_legacy(
    scenario_classes: list,
    max_attempts: int,
) -> tuple[list[tuple[str, bool, str | None, float]], int]:
    """Run all scenarios with legacy TEST_EMAIL/TEST_PASSWORD (already in env)."""
    total_failures = 0
    results: list[tuple[str, bool, str | None, float]] = []
    for cls in scenario_classes:
        scenario = cls()
        name = scenario.name
        start = time.monotonic()
        last_error = None
        for attempt in range(1, max_attempts + 1):
            log.info("=== %s — Attempt %d/%d ===", name, attempt, max_attempts)
            success, error = scenario.run()
            last_error = error
            if success:
                duration = time.monotonic() - start
                results.append((name, True, None, duration))
                log.info("%s passed on attempt %d (%.1fs)", name, attempt, duration)
                break
            log.warning("%s failed: %s", name, error)
            if _is_credentials_missing(error or ""):
                results.append((name, False, error, time.monotonic() - start))
                total_failures += 1
                break
            if _is_auth_error(error or ""):
                results.append((name, False, error, time.monotonic() - start))
                total_failures += 1
                break
            if _is_client_not_started(error or ""):
                results.append((name, False, error, time.monotonic() - start))
                total_failures += 1
                break
            if _is_rate_limited(error or "") and attempt < max_attempts:
                time.sleep(RATE_LIMIT_WAIT_SECONDS)
            if attempt < max_attempts:
                scenario.cleanup()
        else:
            results.append((name, False, last_error, time.monotonic() - start))
            total_failures += 1
    return results, total_failures


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
    use_autonomous = bool(admin_email and admin_password)
    use_legacy = bool(test_email and test_password)

    scenario_classes = _discover_scenarios()
    if not scenario_classes:
        log.error("No E2E scenarios found (expected *_scenario.py with BaseScenario subclasses)")
        return 1
    max_attempts = int(os.environ.get("BRANDYBOX_E2E_MAX_ATTEMPTS", str(DEFAULT_MAX_ATTEMPTS)))

    if use_autonomous:
        from tests.e2e.e2e_setup import run_with_autonomous_setup
        sync_folder_env = os.environ.get("BRANDYBOX_SYNC_FOLDER", "").strip()
        sync_folder = Path(sync_folder_env).resolve() if sync_folder_env else None
        base_url = _get_base_url()

        def run_all():
            results, total_failures = _run_all_scenarios_legacy(scenario_classes, max_attempts)
            log.info("--- E2E summary ---")
            for name, ok, err, dur in results:
                status = "PASS" if ok else "FAIL"
                log.info("  %s: %s (%.1fs)%s", name, status, dur, f" — {err}" if err else "")
            success = total_failures == 0
            err = None if success else f"{total_failures} scenario(s) failed"
            return success, err

        success, error = run_with_autonomous_setup(
            admin_email,
            admin_password,
            base_url,
            sync_folder=sync_folder,
            scenario_runner=run_all,
        )
        if not success:
            log.error("E2E failed: %s", error)
            return 1
        return 0
    if use_legacy:
        results, total_failures = _run_all_scenarios_legacy(scenario_classes, max_attempts)
    else:
        log.error(
            "Set either BRANDYBOX_ADMIN_EMAIL and BRANDYBOX_ADMIN_PASSWORD (autonomous), "
            "or BRANDYBOX_TEST_EMAIL and BRANDYBOX_TEST_PASSWORD (legacy). See tests/e2e/README.md"
        )
        return 1

    log.info("--- E2E summary ---")
    for name, ok, err, dur in results:
        status = "PASS" if ok else "FAIL"
        log.info("  %s: %s (%.1fs)%s", name, status, dur, f" — {err}" if err else "")
    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
