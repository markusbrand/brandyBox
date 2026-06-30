import requests
from typing import Optional, Dict, Any

class BrandyBoxAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.access_token: Optional[str] = None

    def login(self, email: str, password: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/auth/login"
        resp = requests.post(url, json={"email": email, "password": password})
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        return data

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.access_token:
            h["Authorization"] = f"Bearer {self.access_token}"
        return h

    def create_user(self, email: str, first_name: str, last_name: str, e2e_return_temp_password: bool = False) -> Dict[str, Any]:
        url = f"{self.base_url}/api/users"
        headers = self._headers()
        if e2e_return_temp_password:
            headers["X-E2E-Return-Temp-Password"] = "true"

        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        }
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def delete_user(self, email: str) -> None:
        import urllib.parse
        encoded_email = urllib.parse.quote(email)
        url = f"{self.base_url}/api/users/{encoded_email}"
        resp = requests.delete(url, headers=self._headers())
        resp.raise_for_status()

    def list_files(self) -> list:
        url = f"{self.base_url}/api/files/list"
        resp = requests.get(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()
