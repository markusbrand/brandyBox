"""Tests for client config: sync folder, base URL, sync state."""

import json
import pytest
from pathlib import Path


def test_get_default_sync_folder() -> None:
    """Default sync folder is ~/brandyBox."""
    from brandybox.config import get_default_sync_folder

    folder = get_default_sync_folder()
    assert folder.name == "brandyBox"
    assert folder == Path.home() / "brandyBox"


def test_get_sync_folder_path_uses_default_when_no_config(monkeypatch, tmp_path: Path) -> None:
    """When config file does not exist, get_sync_folder_path returns default."""
    from brandybox import config

    monkeypatch.setattr(config, "get_config_path", lambda: tmp_path / "config.json")
    # Config file does not exist
    path = config.get_sync_folder_path()
    assert path == config.get_default_sync_folder()


def test_set_and_get_sync_folder_path(monkeypatch, tmp_path: Path) -> None:
    """set_sync_folder_path persists; get_sync_folder_path returns it."""
    from brandybox import config

    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config, "get_config_path", lambda: config_path)
    folder = tmp_path / "my_sync"
    folder.mkdir()
    config.set_sync_folder_path(folder)
    assert config_path.exists()
    assert config.get_sync_folder_path() == folder


def test_user_has_set_sync_folder_false_when_empty(monkeypatch, tmp_path: Path) -> None:
    """user_has_set_sync_folder is False when config missing or has no sync_folder."""
    from brandybox import config

    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config, "get_config_path", lambda: config_path)
    assert config.user_has_set_sync_folder() is False
    config_path.write_text("{}", encoding="utf-8")
    assert config.user_has_set_sync_folder() is False


def test_user_has_set_sync_folder_true_when_set(monkeypatch, tmp_path: Path) -> None:
    """user_has_set_sync_folder is True when config has sync_folder."""
    from brandybox import config

    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config, "get_config_path", lambda: config_path)
    config_path.write_text(json.dumps({"sync_folder": str(tmp_path)}), encoding="utf-8")
    assert config.user_has_set_sync_folder() is True


def test_get_set_base_url_mode(monkeypatch, tmp_path: Path) -> None:
    """get_base_url_mode and set_base_url_mode round-trip."""
    from brandybox import config

    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config, "get_config_path", lambda: config_path)
    assert config.get_base_url_mode() == "automatic"
    config.set_base_url_mode("manual")
    assert config.get_base_url_mode() == "manual"


def test_get_set_manual_base_url(monkeypatch, tmp_path: Path) -> None:
    """get_manual_base_url and set_manual_base_url round-trip."""
    from brandybox import config

    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config, "get_config_path", lambda: config_path)
    default = config.get_manual_base_url()
    assert default.startswith("http")
    config.set_manual_base_url("https://custom.example.com")
    assert config.get_manual_base_url() == "https://custom.example.com"


def test_clear_sync_state(monkeypatch, tmp_path: Path) -> None:
    """clear_sync_state writes paths list to sync_state path."""
    from brandybox import config

    state_path = tmp_path / "sync_state.json"
    monkeypatch.setattr(config, "get_sync_state_path", lambda: state_path)
    config.clear_sync_state()
    assert state_path.exists()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data.get("paths") == []
