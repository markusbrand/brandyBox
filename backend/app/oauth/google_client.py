"""Google OAuth token and userinfo (async httpx)."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import Settings

log = logging.getLogger(__name__)


async def exchange_authorization_code(
    settings: Settings,
    *,
    code: str,
    redirect_uri: str,
) -> Optional[dict[str, Any]]:
    """Exchange authorization code for token JSON (includes access_token, id_token, …)."""
    if not settings.google_client_id or not settings.google_client_secret:
        log.warning("Google OAuth not configured")
        return None
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
    if resp.status_code != 200:
        log.warning("Google token exchange failed: status=%s body=%s", resp.status_code, resp.text[:500])
        return None
    try:
        return resp.json()
    except Exception as e:
        log.warning("Google token JSON parse failed: %s", e)
        return None


async def fetch_google_userinfo(access_token: str) -> tuple[Optional[str], Optional[str]]:
    """Return (email, sub) from Google userinfo or (None, None) on failure."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        log.warning("Google userinfo failed: status=%s", resp.status_code)
        return None, None
    try:
        data = resp.json()
        email = data.get("email")
        sub = data.get("sub")
        if email:
            return str(email).lower(), str(sub) if sub else None
    except Exception as e:
        log.warning("Google userinfo parse failed: %s", e)
    return None, None
