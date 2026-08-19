import logging
from tests.e2e.large_file_sync_scenario import LargeFileSyncScenario

log = logging.getLogger(__name__)

class ChunkedFileSyncScenario(LargeFileSyncScenario):
    """
    Scenario: create a file larger than 50MB to trigger the chunked upload logic
    in the Tauri client (which triggers at >50MB).
    """

    def __init__(self) -> None:
        super().__init__()
        # Override file size to 52 MB to ensure it crosses the 50MB threshold for chunking
        self._file_size_bytes = 52 * 1024 * 1024
        self._file_name = "autotest_chunked.bin"
        self._test_file_path = self._sync_folder / self._file_name

        # Increase timeout for 52MB file
        self.max_step_duration_seconds = 300

    @property
    def name(self) -> str:
        return "chunked_file_sync"
