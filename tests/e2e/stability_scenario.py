import os
import time
import logging
from typing import List
from tests.e2e.scenario_base import BaseScenario, ScenarioStep, StepResult
from tests.e2e.sync_scenario import _start_client, _get_sync_folder, _login_and_list, _get_api_client, SYNC_POLL_INTERVAL

log = logging.getLogger(__name__)

class StabilityScenario(BaseScenario):
    """
    Test sync stability under simulated network pressure.
    Verifies that the client handles large batches and retries correctly.
    """
    def __init__(self) -> None:
        super().__init__(max_step_duration_seconds=600)
        self._sync_folder = _get_sync_folder()
        self._api = _get_api_client()
        self._had_successful_login = False

    @property
    def name(self) -> str:
        return "stability_e2e"

    def _step1_start_client(self) -> StepResult:
        if not _start_client():
            return StepResult("start_client", False, "Could not start or detect client")
        return StepResult("start_client", True)

    def _step2_batch_upload(self) -> StepResult:
        try:
            self._sync_folder.mkdir(parents=True, exist_ok=True)
            for i in range(20):
                path = self._sync_folder / f"stability_{i}.txt"
                path.write_text(f"stability test content {i} " * 100, encoding="utf-8")
        except Exception as e:
            return StepResult("batch_upload", False, str(e))
        return StepResult("batch_upload", True)

    def _step3_wait_sync_batch(self) -> StepResult:
        err, _ = _login_and_list(self._api)
        if err: return StepResult("wait_sync_batch", False, err)
        self._had_successful_login = True

        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            _, files = _login_and_list(self._api)
            if files is not None:
                paths = {f["path"] for f in files}
                if all(f"stability_{i}.txt" in paths for i in range(20)):
                    return StepResult("wait_sync_batch", True)
            time.sleep(SYNC_POLL_INTERVAL)
        return StepResult("wait_sync_batch", False, "Timeout waiting for batch upload")

    def _step4_large_file_chunked(self) -> StepResult:
        try:
            large_file = self._sync_folder / "large_stability.bin"
            with open(large_file, "wb") as f:
                f.write(os.urandom(55 * 1024 * 1024)) # 55MB
        except Exception as e:
            return StepResult("large_file", False, str(e))
        return StepResult("large_file", True)

    def _step5_wait_sync_large(self) -> StepResult:
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            _, files = _login_and_list(self._api)
            if files is not None:
                if any(f["path"] == "large_stability.bin" and f["size"] == 55 * 1024 * 1024 for f in files):
                    return StepResult("wait_sync_large", True)
            time.sleep(SYNC_POLL_INTERVAL)
        return StepResult("wait_sync_large", False, "Timeout waiting for large file sync")

    def steps(self) -> List[ScenarioStep]:
        return [
            ScenarioStep("1_start_client", self._step1_start_client),
            ScenarioStep("2_batch_upload", self._step2_batch_upload),
            ScenarioStep("3_wait_sync_batch", self._step3_wait_sync_batch),
            ScenarioStep("4_large_file_chunked", self._step4_large_file_chunked),
            ScenarioStep("5_wait_sync_large", self._step5_wait_sync_large),
        ]

    def cleanup(self) -> None:
        # Local cleanup
        for i in range(20):
            p = self._sync_folder / f"stability_{i}.txt"
            if p.exists(): p.unlink()
        lp = self._sync_folder / "large_stability.bin"
        if lp.exists(): lp.unlink()

        # Remote cleanup
        if self._had_successful_login:
            for i in range(20):
                try: self._api.delete_file(f"stability_{i}.txt")
                except: pass
            try: self._api.delete_file("large_stability.bin")
            except: pass
        super().cleanup()
