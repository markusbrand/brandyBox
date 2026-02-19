"""Load E2E environment variables from repo-root .env (no extra dependency)."""
import os
from pathlib import Path


def load_e2e_env(repo_root: Path) -> None:
    """
    Load key=value lines from repo_root/.env into os.environ.
    Only sets variables that are not already set (environment wins over file).
    """
    env_file = repo_root / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip().strip("'\"")
