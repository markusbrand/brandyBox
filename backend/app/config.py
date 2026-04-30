"""Configuration from environment (no hardcoded secrets)."""

from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _empty_to_none_str(v: object) -> Optional[str]:
    if v is None or v == "":
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return str(v)


# backend/.env — loaded when present (local dev); Docker/production typically inject env instead.
_BACKEND_ENV = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Backend settings from env."""

    model_config = SettingsConfigDict(
        env_prefix="BRANDYBOX_",
        extra="ignore",
        env_file=_BACKEND_ENV,
        env_file_encoding="utf-8",
    )

    # Storage
    storage_base_path: Path = Path("/mnt/shared_storage/brandyBox")
    # Optional hard cap for a single upload body (bytes). Unset = no cap beyond quota and reverse-proxy limits.
    # Set e.g. under Cloudflare Free (100 MB) to fail fast with 413 instead of a truncated or timed-out upload.
    max_single_upload_bytes: int | None = None
    # Optional: path used for "Server disk (Pi)" stats in Settings. If set, disk usage is reported
    # for this path's filesystem (e.g. /mnt/shared_storage to show full HDD). If unset, uses storage_base_path.
    server_disk_path: Path | None = None
    db_path: Path = Path("/data/brandybox.db")
    # Maximum storage for all users: fixed size (e.g. "500GB", "1TB") or percentage of drive (e.g. "70%").
    # Default: use 70% of the available space on the drive containing storage_base_path.
    storage_limit: str = "70%"

    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # Long-lived refresh token (Dropbox-style): user stays logged in without re-login.
    # Override with BRANDYBOX_REFRESH_TOKEN_EXPIRE_DAYS (e.g. 3650 for ~10 years).
    refresh_token_expire_days: int = 365

    # SMTP (for sending passwords to new users)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # First admin (bootstrap)
    admin_email: str = ""
    admin_initial_password: str = ""

    # CORS: set as comma-separated string in env (e.g. https://brandybox.example.com)
    # so pydantic-settings does not try to JSON-decode it
    cors_origins: str = "https://brandybox.brandstaetter.rocks"

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins as a list (split on comma)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or [
            "https://brandybox.brandstaetter.rocks"
        ]

    # Server
    port: int = 8080

    # Optional: path to built web SPA (index.html). Unset = do not mount static app.
    static_dist_path: Optional[Path] = None

    # Public URL used for OAuth redirect_uri when reverse proxies hide the real host (e.g. Cloudflare).
    # Example: https://brandybox.brandstaetter.rocks — must match Google Cloud redirect URI registration.
    public_base_url: Optional[str] = None

    # Google OAuth (optional; leave client_id empty to disable "Sign in with Google")
    google_client_id: str = ""
    google_client_secret: str = ""

    @field_validator("static_dist_path", mode="before")
    @classmethod
    def parse_static_dist(cls, v: object) -> Optional[Path]:
        if v is None or v == "":
            return None
        return Path(str(v))

    @field_validator("public_base_url", mode="before")
    @classmethod
    def parse_public_base(cls, v: object) -> Optional[str]:
        return _empty_to_none_str(v)

    # API / client compatibility (shown in /api/meta/version and client ping)
    api_version: str = "0.2.0"
    min_supported_client_version: str = "0.1.0"

    # Telemetry: prune server_events older than this many days (0 = no prune on write path)
    server_events_retention_days: int = 30

    # Logging (empty log_file = stderr only; level DEBUG|INFO|WARNING|ERROR)
    log_level: str = "INFO"
    log_file: str = ""


def get_settings() -> Settings:
    """Return application settings."""
    return Settings()
