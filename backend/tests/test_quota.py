import pytest
from pathlib import Path
from app.files.quota import get_drive_stats

def test_get_drive_stats_success(monkeypatch, tmp_path):
    """Test get_drive_stats returns correct tuple on success."""
    import shutil
    from collections import namedtuple
    Usage = namedtuple("usage", ["total", "free"])
    def mock_disk_usage(path):
        return Usage(total=1000, free=500)

    monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)
    assert get_drive_stats(tmp_path) == (1000, 500)

def test_get_drive_stats_oserror(monkeypatch, tmp_path):
    """Test get_drive_stats returns (0, 0) and logs a warning on OSError."""
    import shutil
    def mock_disk_usage(path):
        raise OSError("Mocked OSError")

    monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)
    assert get_drive_stats(tmp_path) == (0, 0)

def test_get_drive_stats_attributeerror(monkeypatch, tmp_path):
    """Test get_drive_stats returns (0, 0) and logs a warning on AttributeError."""
    import shutil
    def mock_disk_usage(path):
        raise AttributeError("Mocked AttributeError")

    monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)
    assert get_drive_stats(tmp_path) == (0, 0)
