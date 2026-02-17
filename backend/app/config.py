"""Configuration from environment (no hardcoded secrets)."""

from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend settings from env."""

    model_config = SettingsConfigDict(env_prefix="BRANDYBOX_", extra="ignore")

    # Storage
    storage_base_path: Path = Path("/mnt/shared_storage/brandyBox")
    db_path: Path = Path("/data/brandybox.db")

    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

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

    # Logging (empty log_file = stderr only; level DEBUG|INFO|WARNING|ERROR)
    log_level: str = "INFO"
    log_file: str = ""


def get_settings() -> Settings:
    """Return application settings."""
    return Settings()
