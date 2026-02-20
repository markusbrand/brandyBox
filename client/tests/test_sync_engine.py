"""Tests for sync engine: list local, load/save state, sync_run with mocked API."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from brandybox.sync.engine import (
    SYNC_IGNORE_BASENAMES,
    _is_ignored,
    _list_local,
    _load_last_synced_paths,
    _remote_to_set,
    _save_last_synced_paths,
    SyncEngine,
    sync_run,
)


def test_list_local_empty_dir(tmp_path: Path) -> None:
    """_list_local on empty dir returns empty list."""
    assert _list_local(tmp_path) == []


def test_list_local_nested_files(tmp_path: Path) -> None:
    """_list_local returns relative paths with forward slashes and mtimes."""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "f1.txt").write_text("1")
    (tmp_path / "a" / "f2.txt").write_text("2")
    (tmp_path / "top.txt").write_text("top")
    result = _list_local(tmp_path)
    paths = {p for p, _ in result}
    assert paths == {"top.txt", "a/f1.txt", "a/f2.txt"}
    for _, mtime in result:
        assert isinstance(mtime, (int, float))


def test_is_ignored() -> None:
    """_is_ignored returns True for SYNC_IGNORE_BASENAMES, False for others."""
    for name in SYNC_IGNORE_BASENAMES:
        assert _is_ignored(name) is True
        assert _is_ignored(f"subdir/{name}") is True
    assert _is_ignored("normal.txt") is False
    assert _is_ignored("a/b/c.txt") is False
    assert _is_ignored(".directory.bak") is False  # basename is .directory.bak, not in set
    # .git paths are ignored (avoid permission issues and keep sync content-only)
    assert _is_ignored("Settings and programs/PycharmProjects/webcrawl/.git/objects/72/b5f82560debad7a1f1c2a76b52be96d44d4d81") is True
    assert _is_ignored(".git/HEAD") is True
    assert _is_ignored("repo/.git/config") is True
    assert _is_ignored("docs/readme.txt") is False  # no .git in path


def test_list_local_excludes_ignored_basenames(tmp_path: Path) -> None:
    """_list_local does not include files whose basename is in SYNC_IGNORE_BASENAMES."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "doc.txt").write_text("content")
    (tmp_path / ".directory").write_text("")
    (tmp_path / "Thumbs.db").write_text("")
    (tmp_path / "sub" / ".DS_Store").write_text("")
    (tmp_path / "sub" / "real.txt").write_text("x")
    result = _list_local(tmp_path)
    paths = {p for p, _ in result}
    assert paths == {"doc.txt", "sub/real.txt"}
    assert ".directory" not in paths
    assert "Thumbs.db" not in paths
    assert "sub/.DS_Store" not in paths


def test_list_local_excludes_git_paths(tmp_path: Path) -> None:
    """_list_local does not include files under .git (avoids permission issues)."""
    (tmp_path / "proj").mkdir()
    (tmp_path / "proj" / ".git").mkdir()
    (tmp_path / "proj" / ".git" / "objects").mkdir()
    (tmp_path / "proj" / ".git" / "objects" / "ab").mkdir()
    (tmp_path / "proj" / ".git" / "objects" / "ab" / "cdef123").write_text("")
    (tmp_path / "proj" / "readme.txt").write_text("hi")
    result = _list_local(tmp_path)
    paths = {p for p, _ in result}
    assert "proj/readme.txt" in paths
    assert not any(".git" in p for p in paths)


def test_remote_to_set() -> None:
    """_remote_to_set converts API list to set of (path, mtime)."""
    remote = [{"path": "a.txt", "mtime": 100.0}, {"path": "b/c.txt", "mtime": 200.0}]
    got = _remote_to_set(remote)
    assert got == {("a.txt", 100.0), ("b/c.txt", 200.0)}


def test_load_last_synced_paths_empty(monkeypatch, tmp_path: Path) -> None:
    """_load_last_synced_paths returns empty set when file missing."""
    from brandybox.sync import engine

    state_path = tmp_path / "sync_state.json"
    monkeypatch.setattr(engine, "get_sync_state_path", lambda: state_path)
    assert _load_last_synced_paths() == set()


def test_save_and_load_last_synced_paths(monkeypatch, tmp_path: Path) -> None:
    """_save_last_synced_paths persists; _load_last_synced_paths reads back."""
    from brandybox.sync import engine

    state_path = tmp_path / "sync_state.json"
    monkeypatch.setattr(engine, "get_sync_state_path", lambda: state_path)
    paths = {"a.txt", "b/c.txt"}
    _save_last_synced_paths(paths)
    assert state_path.exists()
    assert _load_last_synced_paths() == paths


def test_sync_run_list_failure_returns_error(tmp_path: Path) -> None:
    """sync_run returns error message when API list_files raises."""
    api = MagicMock()
    api.list_files.side_effect = Exception("network error")
    err = sync_run(api, tmp_path)
    assert err is not None
    assert "network error" in err


def test_sync_run_success_empty(monkeypatch, tmp_path: Path) -> None:
    """sync_run with no local/remote files completes and returns None."""
    from brandybox.sync import engine

    state_path = tmp_path / "sync_state.json"
    monkeypatch.setattr(engine, "get_sync_state_path", lambda: state_path)
    api = MagicMock()
    api.list_files.return_value = []
    err = sync_run(api, tmp_path)
    assert err is None


def test_sync_engine_run_delegates_to_sync_run(monkeypatch, tmp_path: Path) -> None:
    """SyncEngine.run() calls sync_run and returns same result."""
    from brandybox.sync import engine

    state_path = tmp_path / "sync_state.json"
    monkeypatch.setattr(engine, "get_sync_state_path", lambda: state_path)
    api = MagicMock()
    api.list_files.return_value = []
    engine_instance = SyncEngine(api, tmp_path)
    err = engine_instance.run()
    assert err is None
    api.list_files.assert_called_once()
