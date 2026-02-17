"""Entry point: auth, login or tray, sync loop."""

from brandybox.api.client import BrandyBoxAPI
from brandybox.auth.credentials import CredentialsStore
from brandybox.tray import run_tray
from brandybox.ui.settings import show_login


def main() -> None:
    """Run the Brandy Box desktop application."""
    api = BrandyBoxAPI()
    creds = CredentialsStore()
    access_token = creds.get_valid_access_token(api)
    if access_token:
        run_tray(api, access_token)
        return
    # No valid credentials: show login
    def on_success(email: str, password: str) -> None:
        data = api.login(email, password)
        creds.set_stored(email, data["refresh_token"])
        run_tray(api, data["access_token"])
    show_login(on_success=on_success, on_cancel=lambda: None)


if __name__ == "__main__":
    main()
