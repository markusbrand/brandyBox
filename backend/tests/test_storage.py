"""Tests for file storage path resolution."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.files.storage import (
    delete_file,
    list_files_recursive,
    resolve_user_path,
    user_base_path,
)


def test_user_base_path(monkeypatch):
    """User base path is base / email."""
    from app.files import storage
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/mnt/shared_storage/brandyBox")
    monkeypatch.setattr(storage, "get_settings", lambda: mock_settings)
    base = user_base_path("markus@brandstaetter.rocks")
    assert base == Path("/mnt/shared_storage/brandyBox/markus@brandstaetter.rocks")


def test_resolve_user_path_rejects_traversal(monkeypatch):
    """Relative path with .. raises ValueError."""
    from app.files import storage
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/data")
    monkeypatch.setattr(storage, "get_settings", lambda: mock_settings)
    with pytest.raises(ValueError):
        resolve_user_path("a@b.co", "../../etc/passwd")


def test_resolve_user_path_safe(monkeypatch):
    """Safe relative path is resolved under user base."""
    from app.files import storage
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/data/brandyBox")
    monkeypatch.setattr(storage, "get_settings", lambda: mock_settings)
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


def test_delete_file(monkeypatch, tmp_path):
    """delete_file removes file under user base; raises if not found or not a file."""
    from app.files import storage
    mock_settings = MagicMock()
    mock_settings.storage_base_path = tmp_path
    monkeypatch.setattr(storage, "get_settings", lambda: mock_settings)
    user_dir = tmp_path / "u@x.co"
    user_dir.mkdir()
    (user_dir / "foo").mkdir()
    target = user_dir / "foo" / "bar.txt"
    target.write_text("content")
    delete_file("u@x.co", "foo/bar.txt")
    assert not target.exists()
    with pytest.raises(FileNotFoundError):
        delete_file("u@x.co", "foo/bar.txt")
    with pytest.raises(ValueError):
        delete_file("u@x.co", "../../etc/passwd")
