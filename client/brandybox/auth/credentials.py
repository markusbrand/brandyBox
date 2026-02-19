"""Keyring-backed credential storage and token refresh."""

import logging
import os
from typing import Optional, Tuple

import keyring

from brandybox.api.client import BrandyBoxAPI

log = logging.getLogger(__name__)

KEY_EMAIL = "email"
KEY_REFRESH_TOKEN = "refresh_token"


def _keyring_service_name() -> str:
    """Use a separate keyring namespace when BRANDYBOX_CONFIG_DIR is set (E2E)."""
    if os.environ.get("BRANDYBOX_CONFIG_DIR", "").strip():
        return "BrandyBox-E2E"
    return "BrandyBox"


class CredentialsStore:
    """
    Stores email and refresh token in OS keyring (Windows Credential Manager,
    macOS Keychain, Linux Secret Service). No plain-text password storage.
    """

    def __init__(self) -> None:
        self._keyring = keyring.get_keyring()

    def get_stored(self) -> Optional[Tuple[str, str]]:
        """
        Return (email, refresh_token) if stored, else None.
        On keyring read error (e.g. UnicodeDecodeError from corrupted entry), returns None
        so the app can show login and overwrite the entry.
        """
        try:
            service = _keyring_service_name()
            email = keyring.get_password(service, KEY_EMAIL)
            token = keyring.get_password(service, KEY_REFRESH_TOKEN)
        except Exception as e:
            log.warning("Could not read stored credentials: %s", e)
            return None
        if email and token:
            return (email, token)
        return None

    def set_stored(self, email: str, refresh_token: str) -> None:
        """Store email and refresh token in keyring."""
        service = _keyring_service_name()
        keyring.set_password(service, KEY_EMAIL, email)
        keyring.set_password(service, KEY_REFRESH_TOKEN, refresh_token)

    def clear_stored(self) -> None:
        """Remove stored credentials."""
        service = _keyring_service_name()
        try:
            keyring.delete_password(service, KEY_EMAIL)
        except keyring.errors.PasswordDeleteError:
            pass
        try:
            keyring.delete_password(service, KEY_REFRESH_TOKEN)
        except keyring.errors.PasswordDeleteError:
            pass

    def get_valid_access_token(self, api: BrandyBoxAPI) -> Optional[str]:
        """
        If we have stored refresh token, try to refresh and return new access token.
        Updates stored refresh token on success. Returns None if no credentials or refresh fails.
        """
        stored = self.get_stored()
        if not stored:
            log.debug("No stored credentials")
            return None
        email, refresh_token = stored
        try:
            data = api.refresh(refresh_token)
            self.set_stored(email, data["refresh_token"])
            log.debug("Token refresh successful for %s", email)
            return data["access_token"]
        except Exception as e:
            log.warning("Token refresh failed: %s", e)
            return None
