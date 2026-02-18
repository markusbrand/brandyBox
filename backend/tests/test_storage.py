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


def test_resolve_user_path_rejects_unsafe_segment(monkeypatch) -> None:
    """Path segment with invalid characters (e.g. semicolon, percent) raises ValueError."""
    from app.files import storage
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/data")
    monkeypatch.setattr(storage, "get_settings", lambda: mock_settings)
    with pytest.raises(ValueError, match="Unsafe path segment"):
        resolve_user_path("a@b.co", "file%;.txt")
    with pytest.raises(ValueError, match="Unsafe path segment"):
        resolve_user_path("a@b.co", "dir/file\x00name.txt")


def test_resolve_user_path_rejects_dot_segment(monkeypatch) -> None:
    """Path segment '.' or '..' is rejected."""
    from app.files import storage
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/data")
    monkeypatch.setattr(storage, "get_settings", lambda: mock_settings)
    with pytest.raises(ValueError):
        resolve_user_path("a@b.co", ".")
    with pytest.raises(ValueError):
        resolve_user_path("a@b.co", "sub/..")


def test_resolve_user_path_accepts_spaces_and_parens(monkeypatch) -> None:
    """Safe segment with spaces and parentheses (e.g. 'File (1).txt') is accepted."""
    from app.files import storage
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/data")
    monkeypatch.setattr(storage, "get_settings", lambda: mock_settings)
    got = resolve_user_path("u@x.co", "My File (1).txt")
    assert got == Path("/data/u@x.co/My File (1).txt")


def test_user_base_path_rejects_invalid_email(monkeypatch) -> None:
    """Email with slash or empty raises ValueError."""
    from app.files import storage
    mock_settings = MagicMock()
    mock_settings.storage_base_path = Path("/data")
    monkeypatch.setattr(storage, "get_settings", lambda: mock_settings)
    with pytest.raises(ValueError, match="Invalid email"):
        user_base_path("")
    with pytest.raises(ValueError):
        user_base_path("user/../etc@x.co")


def test_list_files_recursive_nested(tmp_path) -> None:
    """Nested files and dirs are listed with correct relative paths."""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b.txt").write_text("b")
    (tmp_path / "a" / "c.txt").write_text("c")
    (tmp_path / "root.txt").write_text("r")
    result = list_files_recursive(tmp_path)
    paths = {r["path"] for r in result}
    assert paths == {"root.txt", "a/b.txt", "a/c.txt"}
    assert len(result) == 3
