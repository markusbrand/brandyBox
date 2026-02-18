"""Smoke tests: package and main modules import without error."""

import pytest


def test_brandybox_package_imports() -> None:
    """Client package can be imported."""
    import brandybox  # noqa: F401

    assert brandybox.__file__ is not None


def test_config_module_imports() -> None:
    """Config module exposes expected behavior."""
    from brandybox.config import (
        DEFAULT_REMOTE_BASE_URL,
        get_config_path,
        get_base_url_mode,
        get_manual_base_url,
    )

    path = get_config_path()
    assert path is not None
    assert path.suffix == ".json"
    assert get_base_url_mode() in ("automatic", "manual")
    assert isinstance(get_manual_base_url(), str)
    assert DEFAULT_REMOTE_BASE_URL.startswith("http")
