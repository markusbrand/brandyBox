from unittest.mock import patch

from tests.e2e import run_autonomous_sync
from tests.e2e.scenario_base import BaseScenario, ScenarioStep


class DummyScenario(BaseScenario):
    @property
    def name(self) -> str:
        return "DummyScenario"

    def steps(self) -> list[ScenarioStep]:
        return []


def test_run_scenario_with_retries_success():
    scenario = DummyScenario()
    with patch.object(scenario, "run", return_value=(True, None)):
        success, err = run_autonomous_sync._run_scenario_with_retries(scenario, max_attempts=3)
        assert success is True
        assert err is None


def test_run_scenario_with_retries_rate_limit_and_success():
    scenario = DummyScenario()
    with patch.object(scenario, "run", side_effect=[(False, "HTTP 429 Too Many Requests"), (True, None)]), \
         patch("time.sleep") as mock_sleep, \
         patch.object(scenario, "cleanup") as mock_cleanup:
        success, err = run_autonomous_sync._run_scenario_with_retries(scenario, max_attempts=3)
        assert success is True
        assert err is None
        mock_sleep.assert_called_once_with(run_autonomous_sync.RATE_LIMIT_WAIT_SECONDS)
        mock_cleanup.assert_called_once()


def test_run_scenario_with_retries_auth_error_no_retry():
    scenario = DummyScenario()
    with patch.object(scenario, "run", return_value=(False, "401 Unauthorized")), \
         patch.object(scenario, "cleanup") as mock_cleanup:
        success, err = run_autonomous_sync._run_scenario_with_retries(scenario, max_attempts=3)
        assert success is False
        assert "401" in err
        mock_cleanup.assert_not_called()


def test_run_scenario_with_retries_client_not_started_no_retry():
    scenario = DummyScenario()
    with patch.object(scenario, "run", return_value=(False, "Client could not start")), \
         patch.object(scenario, "cleanup") as mock_cleanup:
        success, err = run_autonomous_sync._run_scenario_with_retries(scenario, max_attempts=3)
        assert success is False
        assert "could not start" in err.lower()
        mock_cleanup.assert_not_called()


def test_run_scenario_with_retries_credentials_missing_no_retry():
    scenario = DummyScenario()
    err_msg = "BRANDYBOX_TEST_EMAIL and BRANDYBOX_TEST_PASSWORD not set"
    with patch.object(scenario, "run", return_value=(False, err_msg)), \
         patch.object(scenario, "cleanup") as mock_cleanup:
        success, err = run_autonomous_sync._run_scenario_with_retries(scenario, max_attempts=3)
        assert success is False
        assert err == err_msg
        mock_cleanup.assert_not_called()


def test_run_scenario_with_retries_all_attempts_fail():
    scenario = DummyScenario()
    with patch.object(scenario, "run", return_value=(False, "Some persistent failure")), \
         patch("time.sleep"), \
         patch.object(scenario, "cleanup") as mock_cleanup:
        success, err = run_autonomous_sync._run_scenario_with_retries(scenario, max_attempts=2)
        assert success is False
        assert err == "Some persistent failure"
        assert mock_cleanup.call_count == 1


def test_run_autonomous_mode_success():
    with patch("tests.e2e.e2e_setup.run_with_autonomous_setup", return_value=(True, None)):
        code = run_autonomous_sync._run_autonomous_mode("admin@a.com", "pass", max_attempts=1)
        assert code == 0


def test_run_autonomous_mode_failure():
    with patch("tests.e2e.e2e_setup.run_with_autonomous_setup", return_value=(False, "Setup failed")):
        code = run_autonomous_sync._run_autonomous_mode("admin@a.com", "pass", max_attempts=1)
        assert code == 1


def test_run_legacy_mode_success(monkeypatch):
    monkeypatch.setenv("BRANDYBOX_BASE_URL", "http://localhost:8081")
    with patch("tests.e2e.run_autonomous_sync.SyncE2EScenario"), \
         patch.object(run_autonomous_sync, "_run_scenario_with_retries", return_value=(True, None)):
        code = run_autonomous_sync._run_legacy_mode(max_attempts=1)
        assert code == 0


def test_run_legacy_mode_failure(monkeypatch):
    monkeypatch.setenv("BRANDYBOX_BASE_URL", "http://localhost:8081")
    with patch("tests.e2e.run_autonomous_sync.SyncE2EScenario"), \
         patch.object(run_autonomous_sync, "_run_scenario_with_retries", return_value=(False, "Failed")):
        code = run_autonomous_sync._run_legacy_mode(max_attempts=1)
        assert code == 1


def test_main_no_credentials(monkeypatch):
    monkeypatch.delenv("BRANDYBOX_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("BRANDYBOX_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("BRANDYBOX_TEST_EMAIL", raising=False)
    monkeypatch.delenv("BRANDYBOX_TEST_PASSWORD", raising=False)

    code = run_autonomous_sync.main()
    assert code == 1


def test_main_autonomous_credentials(monkeypatch):
    monkeypatch.setenv("BRANDYBOX_ADMIN_EMAIL", "admin@a.com")
    monkeypatch.setenv("BRANDYBOX_ADMIN_PASSWORD", "pass")
    monkeypatch.delenv("BRANDYBOX_TEST_EMAIL", raising=False)
    monkeypatch.delenv("BRANDYBOX_TEST_PASSWORD", raising=False)

    with patch.object(run_autonomous_sync, "_run_autonomous_mode", return_value=0) as mock_auto:
        code = run_autonomous_sync.main()
        assert code == 0
        mock_auto.assert_called_once_with("admin@a.com", "pass", run_autonomous_sync.DEFAULT_MAX_ATTEMPTS)


def test_main_legacy_credentials(monkeypatch):
    monkeypatch.delenv("BRANDYBOX_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("BRANDYBOX_ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("BRANDYBOX_TEST_EMAIL", "test@a.com")
    monkeypatch.setenv("BRANDYBOX_TEST_PASSWORD", "pass")

    with patch.object(run_autonomous_sync, "_run_legacy_mode", return_value=0) as mock_legacy:
        code = run_autonomous_sync.main()
        assert code == 0
        mock_legacy.assert_called_once_with(run_autonomous_sync.DEFAULT_MAX_ATTEMPTS)
