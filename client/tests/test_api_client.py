"""Tests for BrandyBoxAPI with mocked HTTP."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from brandybox.api.client import BrandyBoxAPI


@pytest.fixture
def mock_httpx_client():
    """Patch httpx.Client so requests return controlled responses."""
    with patch("brandybox.api.client.httpx.Client") as MockClient:
        yield MockClient


def test_login_sets_access_token_and_returns_data(mock_httpx_client) -> None:
    """login() POSTs to /api/auth/login and returns token data."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "access_token": "access-xyz",
        "refresh_token": "refresh-abc",
        "expires_in": 1800,
    }
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance
    mock_httpx_client.return_value.__exit__.return_value = False

    api = BrandyBoxAPI(base_url="https://api.test.com")
    data = api.login("user@example.com", "secret")

    assert data["access_token"] == "access-xyz"
    assert data["refresh_token"] == "refresh-abc"
    assert api._access_token == "access-xyz"
    mock_client_instance.post.assert_called_once()
    call_args = mock_client_instance.post.call_args
    assert "/api/auth/login" in call_args[0][0]
    assert call_args[1]["json"]["email"] == "user@example.com"
    assert call_args[1]["json"]["password"] == "secret"


def test_list_files_returns_list(mock_httpx_client) -> None:
    """list_files() GETs /api/files/list and returns list of dicts."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        {"path": "a.txt", "mtime": 100.0},
        {"path": "b/c.txt", "mtime": 200.0},
    ]
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance
    mock_httpx_client.return_value.__exit__.return_value = False

    api = BrandyBoxAPI(base_url="https://api.test.com", access_token="token")
    result = api.list_files()

    assert len(result) == 2
    assert result[0]["path"] == "a.txt"
    mock_client_instance.get.assert_called_once()
    assert "Authorization" in mock_client_instance.get.call_args[1]["headers"]
    assert "Bearer token" in mock_client_instance.get.call_args[1]["headers"]["Authorization"]


def test_upload_file_posts_path_and_body(mock_httpx_client) -> None:
    """upload_file() POSTs to /api/files/upload with path param and body."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance
    mock_httpx_client.return_value.__exit__.return_value = False

    api = BrandyBoxAPI(base_url="https://api.test.com", access_token="t")
    api.upload_file("docs/file.txt", b"file content")

    mock_client_instance.post.assert_called_once()
    call_kw = mock_client_instance.post.call_args[1]
    assert call_kw["params"]["path"] == "docs/file.txt"
    assert call_kw["content"] == b"file content"


def test_download_file_returns_bytes(mock_httpx_client) -> None:
    """download_file() GETs and returns response content."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.content = b"downloaded bytes"
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance
    mock_httpx_client.return_value.__exit__.return_value = False

    api = BrandyBoxAPI(base_url="https://api.test.com", access_token="t")
    result = api.download_file("a.txt")

    assert result == b"downloaded bytes"
    mock_client_instance.get.assert_called_once()
    assert mock_client_instance.get.call_args[1]["params"]["path"] == "a.txt"


def test_delete_file_treats_404_as_success(mock_httpx_client) -> None:
    """delete_file() does not raise when response is 404."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status = MagicMock()  # would raise on 4xx, but we check status first
    mock_client_instance = MagicMock()
    mock_client_instance.delete.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance
    mock_httpx_client.return_value.__exit__.return_value = False

    api = BrandyBoxAPI(base_url="https://api.test.com", access_token="t")
    api.delete_file("gone.txt")  # should not raise

    mock_client_instance.delete.assert_called_once()


def test_set_base_url_strips_trailing_slash() -> None:
    """set_base_url stores URL without trailing slash."""
    api = BrandyBoxAPI(base_url="https://api.test.com/")
    assert api._base_url == "https://api.test.com"
    api.set_base_url("https://other.test/")
    assert api._base_url == "https://other.test"
