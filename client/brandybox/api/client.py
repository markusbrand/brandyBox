"""HTTP client for Brandy Box backend API."""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from brandybox.network import get_base_url

log = logging.getLogger(__name__)


class BrandyBoxAPI:
    """
    Client for Brandy Box backend: login, refresh, list/upload/download files.
    Uses base URL from network detection (LAN vs Cloudflare).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> None:
        self._base_url = (base_url or get_base_url()).rstrip("/")
        self._access_token = access_token
        log.debug("API client base_url=%s", self._base_url)

    def _headers(self) -> Dict[str, str]:
        out = {"Accept": "application/json"}
        if self._access_token:
            out["Authorization"] = f"Bearer {self._access_token}"
        return out

    def set_access_token(self, token: Optional[str]) -> None:
        """Set or clear the access token."""
        self._access_token = token

    def set_base_url(self, base_url: str) -> None:
        """Update the base URL (e.g. after user changes settings)."""
        self._base_url = (base_url or "").rstrip("/")
        log.debug("API client base_url updated to %s", self._base_url)

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """POST /api/auth/login. Returns {access_token, refresh_token, expires_in}."""
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                f"{self._base_url}/api/auth/login",
                json={"email": email, "password": password},
                headers={"Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
            self._access_token = data["access_token"]
            return data

    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        """POST /api/auth/refresh. Returns new token pair."""
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                f"{self._base_url}/api/auth/refresh",
                json={"refresh_token": refresh_token},
                headers={"Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
            self._access_token = data["access_token"]
            return data

    def me(self) -> Dict[str, Any]:
        """GET /api/users/me. Requires auth."""
        with httpx.Client(timeout=30.0) as client:
            r = client.get(
                f"{self._base_url}/api/users/me",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    def list_files(self) -> List[Dict[str, Any]]:
        """GET /api/files/list. Returns [{path, mtime}, ...]."""
        log.debug("GET /api/files/list")
        with httpx.Client(timeout=60.0) as client:
            r = client.get(
                f"{self._base_url}/api/files/list",
                headers=self._headers(),
            )
            r.raise_for_status()
            data = r.json()
            log.debug("list_files returned %d items", len(data))
            return data

    def upload_file(self, relative_path: str, body: bytes) -> None:
        """POST /api/files/upload?path=... with body."""
        log.debug("upload_file path=%s size=%d", relative_path, len(body))
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                f"{self._base_url}/api/files/upload",
                params={"path": relative_path},
                content=body,
                headers=self._headers(),
            )
            r.raise_for_status()

    def download_file(self, relative_path: str) -> bytes:
        """GET /api/files/download?path=... Returns file bytes."""
        log.debug("download_file path=%s", relative_path)
        with httpx.Client(timeout=60.0) as client:
            r = client.get(
                f"{self._base_url}/api/files/download",
                params={"path": relative_path},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.content

    def delete_file(self, relative_path: str) -> None:
        """DELETE /api/files/delete?path=... Remove file from remote (Raspberry Pi).
        Treats 404 as success (file already gone).
        """
        log.debug("delete_file path=%s", relative_path)
        with httpx.Client(timeout=30.0) as client:
            r = client.delete(
                f"{self._base_url}/api/files/delete",
                params={"path": relative_path},
                headers=self._headers(),
            )
            if r.status_code == 404:
                log.debug("delete_file path=%s: already gone (404)", relative_path)
                return
            r.raise_for_status()

    # --- Admin: user management (admin only) ---

    def list_users(self) -> List[Dict[str, Any]]:
        """GET /api/users. List all users (admin only)."""
        log.debug("GET /api/users")
        with httpx.Client(timeout=30.0) as client:
            r = client.get(
                f"{self._base_url}/api/users",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    def create_user(self, email: str, first_name: str, last_name: str) -> Dict[str, Any]:
        """POST /api/users. Create a new user (admin only). Password is sent by email."""
        log.debug("create_user email=%s", email)
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                f"{self._base_url}/api/users",
                json={"email": email, "first_name": first_name, "last_name": last_name},
                headers={**self._headers(), "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()

    def delete_user(self, email: str) -> None:
        """DELETE /api/users/{email}. Delete a user (admin only)."""
        log.debug("delete_user email=%s", email)
        encoded = quote(email, safe="")
        with httpx.Client(timeout=30.0) as client:
            r = client.delete(
                f"{self._base_url}/api/users/{encoded}",
                headers=self._headers(),
            )
            r.raise_for_status()
