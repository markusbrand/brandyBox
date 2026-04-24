"""Google OAuth: start, callback, token exchange."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token
from app.config import get_settings
from app.db.session import get_db
from app.limiter import limiter
from app.oauth.google_client import exchange_authorization_code, fetch_google_userinfo
from app.oauth.models import OAuthExchange, OAuthState
from app.telemetry.service import log_server_event
from app.users.models import OAuthCompleteRequest, TokenPair
from app.users.service import get_user_by_email

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_SCOPES = "openid email profile"


def _public_origin(settings, request: Request) -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    u = request.base_url
    return f"{u.scheme}://{u.netloc}".rstrip("/")


def _google_redirect_uri(settings, request: Request) -> str:
    return _public_origin(settings, request) + "/api/auth/google/callback"


@router.get("/google/start")
@limiter.limit("30/minute")
async def google_oauth_start(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    """Redirect browser to Google consent screen."""
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured on this server",
        )
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    await session.execute(delete(OAuthState).where(OAuthState.created_at < cutoff))
    state = secrets.token_urlsafe(32)
    session.add(OAuthState(state=state))
    await session.commit()
    redirect_uri = _google_redirect_uri(settings, request)
    from urllib.parse import urlencode

    q = urlencode(
        {
            "client_id": settings.google_client_id,
            "response_type": "code",
            "scope": OAUTH_SCOPES,
            "redirect_uri": redirect_uri,
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
    )
    url = f"{GOOGLE_AUTH}?{q}"
    log.info("Google OAuth start redirect_uri=%s", redirect_uri)
    return RedirectResponse(url=url, status_code=302)


@router.get("/google/callback")
@limiter.exempt
async def google_oauth_callback(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    """Google redirects here; we issue one-time exchange and redirect to SPA login."""
    settings = get_settings()
    base = _public_origin(settings, request)

    def red(path: str) -> RedirectResponse:
        return RedirectResponse(url=f"{base}{path}", status_code=302)

    if error:
        log.warning("Google OAuth error query=%s", error)
        await log_server_event(
            session,
            level="WARNING",
            category="oauth",
            message=f"Google OAuth error: {error}",
        )
        await session.commit()
        return red("/login?error=oauth_denied")

    if not code or not state:
        await log_server_event(
            session,
            level="WARNING",
            category="oauth",
            message="Google OAuth callback missing code or state",
        )
        await session.commit()
        return red("/login?error=oauth_invalid")

    res = await session.execute(select(OAuthState).where(OAuthState.state == state))
    row = res.scalar_one_or_none()
    if not row:
        log.warning("Google OAuth invalid state")
        await log_server_event(
            session,
            level="WARNING",
            category="oauth",
            message="Google OAuth invalid or expired state",
        )
        await session.commit()
        return red("/login?error=oauth_invalid")

    await session.delete(row)
    await session.flush()

    redirect_uri = _google_redirect_uri(settings, request)
    token_json = await exchange_authorization_code(settings, code=code, redirect_uri=redirect_uri)
    if not token_json or "access_token" not in token_json:
        await log_server_event(
            session,
            level="ERROR",
            category="oauth",
            message="Google token exchange failed",
        )
        await session.commit()
        return red("/login?error=oauth_token")

    access = token_json["access_token"]
    email, sub = await fetch_google_userinfo(access)
    if not email:
        await log_server_event(
            session,
            level="ERROR",
            category="oauth",
            message="Google userinfo missing email",
        )
        await session.commit()
        return red("/login?error=oauth_profile")

    user = await get_user_by_email(session, email)
    if not user:
        log.warning("Google OAuth rejected: no local user for email=%s", email)
        await log_server_event(
            session,
            level="INFO",
            category="oauth",
            message="Google OAuth rejected: account not provisioned",
            detail={"email_domain": email.split("@")[-1] if "@" in email else ""},
        )
        await session.commit()
        return red("/login?error=no_account")

    if sub and user.google_sub and user.google_sub != sub:
        log.error("Google sub mismatch for email=%s", email)
        await session.commit()
        return red("/login?error=oauth_account")

    if sub and not user.google_sub:
        user.google_sub = sub
        await session.flush()

    jwt_access = create_access_token(user.email)
    jwt_refresh = create_refresh_token(user.email)
    ex_id = str(uuid.uuid4())
    session.add(
        OAuthExchange(
            id=ex_id,
            access_token=jwt_access,
            refresh_token=jwt_refresh,
        )
    )
    await session.commit()
    log.info("Google OAuth success email=%s exchange issued", email)
    return red(f"/login?exchange={ex_id}")


@router.post("/oauth/complete", response_model=TokenPair)
@limiter.limit("30/minute")
async def oauth_complete(
    request: Request,
    body: OAuthCompleteRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    """Redeem one-time exchange id for JWT pair (SPA)."""
    res = await session.execute(select(OAuthExchange).where(OAuthExchange.id == body.exchange.strip()))
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired exchange")

    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(minutes=2):
        await session.delete(row)
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Exchange expired")

    access = row.access_token
    refresh = row.refresh_token
    await session.delete(row)
    await session.commit()

    settings = get_settings()
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )
