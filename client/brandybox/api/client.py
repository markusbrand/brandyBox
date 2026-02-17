"""HTTP client for Brandy Box backend API."""

from typing import Any, Dict, List, Optional

import httpx

from brandybox.network import get_base_url


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

    def _headers(self) -> Dict[str, str]:
        out = {"Accept": "application/json"}
        if self._access_token:
            out["Authorization"] = f"Bearer {self._access_token}"
        return out

    def set_access_token(self, token: Optional[str]) -> None:
        """Set or clear the access token."""
        self._access_token = token

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
        with httpx.Client(timeout=60.0) as client:
            r = client.get(
                f"{self._base_url}/api/files/list",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    def upload_file(self, relative_path: str, body: bytes) -> None:
        """POST /api/files/upload?path=... with body."""
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
        with httpx.Client(timeout=60.0) as client:
            r = client.get(
                f"{self._base_url}/api/files/download",
                params={"path": relative_path},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.content
