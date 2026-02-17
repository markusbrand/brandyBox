"""Tests for file storage path resolution."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.files.storage import (
    list_files_recursive,
    resolve_user_path,
    user_base_path,
)


def test_user_base_path(monkeypatch):
    """User base path is base / email."""
    from app import config
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/mnt/shared_storage/brandyBox")
    monkeypatch.setattr(config, "get_settings", lambda: mock_settings)
    base = user_base_path("markus@brandstaetter.rocks")
    assert base == Path("/mnt/shared_storage/brandyBox/markus@brandstaetter.rocks")


def test_resolve_user_path_rejects_traversal(monkeypatch):
    """Relative path with .. raises ValueError."""
    from app import config
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/data")
    monkeypatch.setattr(config, "get_settings", lambda: mock_settings)
    with pytest.raises(ValueError):
        resolve_user_path("a@b.co", "../../etc/passwd")


def test_resolve_user_path_safe(monkeypatch):
    """Safe relative path is resolved under user base."""
    from app import config
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/data/brandyBox")
    monkeypatch.setattr(config, "get_settings", lambda: mock_settings)
    got = resolve_user_path("u@x.co", "foo/bar.txt")
    assert got == Path("/data/brandyBox/u@x.co/foo/bar.txt")


def test_list_files_recursive_empty_dir(tmp_path):
    """Empty dir returns empty list."""
    assert list_files_recursive(tmp_path) == []


def test_list_files_recursive_one_file(tmp_path):
    """Single file is listed with path and mtime."""
    (tmp_path / "a.txt").write_text("hi")
    result = list_files_recursive(tmp_path)
    assert len(result) == 1
    assert result[0]["path"] == "a.txt"
    assert "mtime" in result[0]
