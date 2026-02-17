"""Base for extensible E2E test scenarios with cleanup and retry support."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, Tuple

log = logging.getLogger(__name__)


class StepResult:
    """Result of a single scenario step."""

    def __init__(self, name: str, success: bool, message: str = "", details: Any = None) -> None:
        self.name = name
        self.success = success
        self.message = message
        self.details = details

    def __bool__(self) -> bool:
        return self.success


class ScenarioStep:
    """A single step: (name, run_callable, optional_cleanup_callable)."""

    def __init__(
        self,
        name: str,
        run: Callable[[], StepResult],
        cleanup: Optional[Callable[[], None]] = None,
    ) -> None:
        self.name = name
        self.run = run
        self.cleanup = cleanup


class BaseScenario(ABC):
    """
    Extensible E2E scenario: ordered steps and a cleanup phase for recovery on failure.
    Subclass and implement steps() and cleanup().
    """

    def __init__(self, max_step_duration_seconds: float = 300.0) -> None:
        self.max_step_duration_seconds = max_step_duration_seconds
        self._last_failed_step: Optional[str] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Scenario name for logging."""
        ...

    @abstractmethod
    def steps(self) -> List[ScenarioStep]:
        """Ordered list of steps. Each step has run() and optional cleanup()."""
        ...

    def cleanup(self) -> None:
        """
        Called when the scenario fails, before retry. Override to remove test artifacts,
        restart services, etc., so the next run can succeed.
        """
        for step in reversed(self.steps()):
            if step.cleanup:
                try:
                    log.info("Cleanup: %s", step.name)
                    step.cleanup()
                except Exception as e:
                    log.warning("Cleanup step %s failed: %s", step.name, e)

    def run(self) -> Tuple[bool, Optional[str]]:
        """
        Run all steps in order. Returns (success, error_message).
        On first failure, sets _last_failed_step and returns.
        """
        self._last_failed_step = None
        for step in self.steps():
            log.info("Step: %s", step.name)
            try:
                result = step.run()
            except Exception as e:
                log.exception("Step %s raised: %s", step.name, e)
                self._last_failed_step = step.name
                return False, f"{step.name}: {e!s}"
            if not result:
                self._last_failed_step = step.name
                return False, result.message or step.name
        return True, None
