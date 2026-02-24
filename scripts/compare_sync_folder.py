#!/usr/bin/env python3
"""Compare local sync folder with server file list. Uses Brandy Box config and API.
Run from repo root: python scripts/compare_sync_folder.py
Optional: COMPARE_SYNC_FOLDER=C:\path\to\folder to override sync folder."""

import os
import sys

# Run from repo root so brandybox can be found
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, "client"))

from pathlib import Path

from brandybox.api.client import BrandyBoxAPI
from brandybox.auth.credentials import CredentialsStore
from brandybox.config import get_sync_folder_path
from brandybox.network import get_base_url
from brandybox.sync.engine import _is_ignored, _list_local


def main() -> None:
    folder = os.environ.get("COMPARE_SYNC_FOLDER")
    if folder:
        local_root = Path(folder).resolve()
    else:
        local_root = get_sync_folder_path()
    print(f"Local folder: {local_root}")
    if not local_root.is_dir():
        print("Error: folder does not exist.")
        sys.exit(1)

    local_list = _list_local(local_root)
    local_paths = {p for p, _ in local_list if not _is_ignored(p)}
    print(f"Local files (excluding .git and ignore list): {len(local_paths)}")

    api = BrandyBoxAPI()
    api.set_base_url(get_base_url())
    creds = CredentialsStore()
    token = creds.get_valid_access_token(api)
    if not token:
        print("Error: no valid credentials. Log in with the Brandy Box client first.")
        sys.exit(1)
    api.set_access_token(token)

    print("Fetching server file list...")
    remote_list = api.list_files()
    remote_paths = {item["path"] for item in remote_list if not _is_ignored(item["path"])}
    print(f"Server files: {len(remote_paths)}")

    only_local = sorted(local_paths - remote_paths)
    only_server = sorted(remote_paths - local_paths)
    in_both = local_paths & remote_paths

    print()
    print(f"In both:        {len(in_both)}")
    print(f"Only on local:  {len(only_local)}")
    print(f"Only on server: {len(only_server)}")

    if only_local:
        print()
        print("Only on local (first 50):")
        for p in only_local[:50]:
            print(f"  {p}")
        if len(only_local) > 50:
            print(f"  ... and {len(only_local) - 50} more")
    if only_server:
        print()
        print("Only on server (first 50):")
        for p in only_server[:50]:
            print(f"  {p}")
        if len(only_server) > 50:
            print(f"  ... and {len(only_server) - 50} more")

    if not only_local and not only_server:
        print()
        print("Match: local and server have the same set of files.")
    else:
        print()
        print("Difference: run sync in the client to align them.")


if __name__ == "__main__":
    main()
