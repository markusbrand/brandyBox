"""E2E scenario: create a large file in sync dir, wait for sync, verify on server, delete, verify removed."""

import logging
import os
import time
from pathlib import Path
from typing import List

from tests.e2e.scenario_base import BaseScenario, ScenarioStep, StepResult
from tests.e2e.sync_scenario import (
    SYNC_POLL_INTERVAL,
    SYNC_WAIT_TIMEOUT,
    _get_api_client,
    _get_sync_folder,
    _login_and_list,
    _start_client,
)

log = logging.getLogger(__name__)

# Large file artifact (single file; size from env)
LARGE_FILE_NAME = "autotest_large.bin"
# Default 2 MiB; override with BRANDYBOX_LARGE_FILE_SIZE_MB (e.g. 5 or 10)
DEFAULT_LARGE_FILE_SIZE_MB = 2


def _large_file_size_bytes() -> int:
    """Size of the large test file in bytes (from env or default)."""
    s = os.environ.get("BRANDYBOX_LARGE_FILE_SIZE_MB", str(DEFAULT_LARGE_FILE_SIZE_MB)).strip()
    try:
        mb = float(s)
        return max(1, int(mb * 1024 * 1024))
    except ValueError:
        return DEFAULT_LARGE_FILE_SIZE_MB * 1024 * 1024


class LargeFileSyncScenario(BaseScenario):
    """
    Scenario: create one large file (configurable MiB) in sync dir, wait for sync,
    verify on server, delete locally, wait for sync, verify removed.
    Records timing in step details for performance summary.
    """

    def __init__(self) -> None:
        # Large files may need longer sync; use 2x default timeout
        super().__init__(max_step_duration_seconds=SYNC_WAIT_TIMEOUT * 2)
        self._sync_folder = _get_sync_folder()
        self._api = _get_api_client()
        self._test_file_path = self._sync_folder / LARGE_FILE_NAME
        self._file_size_bytes = _large_file_size_bytes()
        self._had_successful_login = False

    @property
    def name(self) -> str:
        return "large_file_sync"

    def _step1_start_client(self) -> StepResult:
        if not _start_client():
            return StepResult("start_client", False, "Could not start or detect client")
        return StepResult("start_client", True)

    def _step2_create_large_file(self) -> StepResult:
        try:
            self._sync_folder.mkdir(parents=True, exist_ok=True)
            # Write in chunks to avoid huge in-memory string
            chunk = b"x" * (256 * 1024)  # 256 KiB
            remaining = self._file_size_bytes
            start = time.monotonic()
            with open(self._test_file_path, "wb") as f:
                while remaining > 0:
                    write_size = min(len(chunk), remaining)
                    f.write(chunk[:write_size])
                    remaining -= write_size
            duration = time.monotonic() - start
            log.info("Created %s (%d bytes) in %.1fs", LARGE_FILE_NAME, self._file_size_bytes, duration)
        except Exception as e:
            return StepResult("create_large_file", False, str(e))
        return StepResult(
            "create_large_file",
            True,
            details={"size_bytes": self._file_size_bytes, "create_duration_seconds": round(duration, 2)},
        )

    def _step3_wait_sync_after_create(self) -> StepResult:
        err, files = _login_and_list(self._api)
        if err:
            return StepResult("wait_sync_create", False, err)
        self._had_successful_login = True
        log.info(
            "Waiting for %s on server (sync folder: %s). Polling every %ds for up to %.0fs.",
            LARGE_FILE_NAME,
            self._sync_folder,
            SYNC_POLL_INTERVAL,
            self.max_step_duration_seconds,
        )
        deadline = time.monotonic() + self.max_step_duration_seconds
        start = time.monotonic()
        last_paths = set()
        while time.monotonic() < deadline:
            _, files = _login_and_list(self._api)
            if files is not None:
                last_paths = {f["path"] for f in files}
                if LARGE_FILE_NAME in last_paths:
                    duration = time.monotonic() - start
                    log.info("Large file appeared on server after %.1fs", duration)
                    return StepResult(
                        "wait_sync_create",
                        True,
                        details={"sync_wait_seconds": round(duration, 2), "size_bytes": self._file_size_bytes},
                    )
            time.sleep(SYNC_POLL_INTERVAL)
        duration = time.monotonic() - start
        log.warning(
            "Timeout: server file list had %d path(s): %s. Ensure client sync folder is %s",
            len(last_paths),
            sorted(last_paths)[:20] if last_paths else "[]",
            self._sync_folder,
        )
        return StepResult(
            "wait_sync_create",
            False,
            f"Timeout waiting for {LARGE_FILE_NAME} on server",
            details={"paths_seen": list(last_paths), "sync_wait_seconds": round(duration, 2)},
        )

    def _step4_verify_server_has_file(self) -> StepResult:
        err, files = _login_and_list(self._api)
        if err:
            return StepResult("verify_after_create", False, err)
        paths = {f["path"] for f in files}
        if LARGE_FILE_NAME not in paths:
            return StepResult("verify_after_create", False, f"Server missing {LARGE_FILE_NAME}", details=paths)
        return StepResult("verify_after_create", True)

    def _step5_delete_local_file(self) -> StepResult:
        try:
            if self._test_file_path.exists():
                self._test_file_path.unlink()
        except Exception as e:
            return StepResult("delete_local", False, str(e))
        return StepResult("delete_local", True)

    def _step6_wait_sync_after_delete(self) -> StepResult:
        err, _ = _login_and_list(self._api)
        if err:
            return StepResult("wait_sync_delete", False, err)
        deadline = time.monotonic() + self.max_step_duration_seconds
        last_paths = set()
        while time.monotonic() < deadline:
            _, files = _login_and_list(self._api)
            if files is not None:
                last_paths = {f["path"] for f in files}
                if LARGE_FILE_NAME not in last_paths:
                    return StepResult("wait_sync_delete", True)
            time.sleep(SYNC_POLL_INTERVAL)
        still = [p for p in last_paths if p == LARGE_FILE_NAME]
        return StepResult(
            "wait_sync_delete",
            False,
            f"Timeout waiting for removal of {LARGE_FILE_NAME} on server",
            details={"paths_still_present": still},
        )

    def _step7_verify_server_deleted(self) -> StepResult:
        err, files = _login_and_list(self._api)
        if err:
            return StepResult("verify_after_delete", False, err)
        paths = {f["path"] for f in files}
        if LARGE_FILE_NAME in paths:
            return StepResult(
                "verify_after_delete",
                False,
                "Server still has large test file after delete",
                details=paths,
            )
        return StepResult("verify_after_delete", True)

    def _cleanup_local(self) -> None:
        try:
            if self._test_file_path.exists():
                self._test_file_path.unlink()
        except OSError as e:
            log.warning("Cleanup local large file: %s", e)

    def _cleanup_remote(self) -> None:
        if not self._had_successful_login:
            return
        err, _ = _login_and_list(self._api)
        if err:
            return
        try:
            self._api.delete_file(LARGE_FILE_NAME)
        except Exception:
            pass

    def steps(self) -> List[ScenarioStep]:
        return [
            ScenarioStep("1_start_client", self._step1_start_client),
            ScenarioStep("2_create_large_file", self._step2_create_large_file),
            ScenarioStep(
                "3_wait_sync_after_create",
                self._step3_wait_sync_after_create,
                cleanup=self._cleanup_local,
            ),
            ScenarioStep("4_verify_server_has_large_file", self._step4_verify_server_has_file),
            ScenarioStep("5_delete_local_large_file", self._step5_delete_local_file),
            ScenarioStep(
                "6_wait_sync_after_delete",
                self._step6_wait_sync_after_delete,
                cleanup=self._cleanup_remote,
            ),
            ScenarioStep("7_verify_server_deleted", self._step7_verify_server_deleted),
        ]

    def cleanup(self) -> None:
        self._cleanup_local()
        self._cleanup_remote()
        super().cleanup()
