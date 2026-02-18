"""Unit tests for file route helpers (path normalization)."""

import pytest

from app.files.routes import _normalize_path_param


def test_normalize_path_param_empty() -> None:
    """None or empty returns empty string."""
    assert _normalize_path_param(None) == ""
    assert _normalize_path_param("") == ""


def test_normalize_path_param_plus_to_space() -> None:
    """Plus signs (URL-encoded space) are converted to space."""
    assert _normalize_path_param("foo+bar") == "foo bar"
    assert _normalize_path_param("a+b+c") == "a b c"


def test_normalize_path_param_unchanged() -> None:
    """Normal path is unchanged."""
    assert _normalize_path_param("documents/file.txt") == "documents/file.txt"
    assert _normalize_path_param("single") == "single"
