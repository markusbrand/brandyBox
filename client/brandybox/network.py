"""Resolve backend base URL: LAN (brandstaetter) vs Cloudflare."""

import logging
import os
import platform
import re
import subprocess
from typing import Optional

import httpx

log = logging.getLogger(__name__)

# Override with BRANDYBOX_BASE_URL if your tunnel uses a path prefix (e.g. https://host/backend)
# Defaults from plan
LAN_HOST = "192.168.0.150"
LAN_NETWORK_NAME = "brandstaetter"
BACKEND_PORT = "8081"
CLOUDFLARE_URL = "https://brandybox.brandstaetter.rocks"

# Short timeout for LAN reachability check (avoid blocking)
LAN_REACH_TIMEOUT = 2.0


def _on_lan_brandstaetter() -> bool:
    """True if current network name matches brandstaetter (SSID or connection name)."""
    system = platform.system()
    try:
        if system == "Windows":
            # netsh wlan show interfaces | findstr SSID
            out = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if out.returncode != 0:
                return False
            match = re.search(r"SSID\s*:\s*(\S+)", out.stdout)
            return bool(match and LAN_NETWORK_NAME.lower() in (match.group(1) or "").lower())
        if system == "Linux":
            # nmcli -t -f NAME connection show --active, or read /proc/net/wireless
            out = subprocess.run(
                ["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if out.returncode != 0:
                return False
            return LAN_NETWORK_NAME.lower() in out.stdout.lower()
        if system == "Darwin":
            # system_profiler SPAirPortDataType | grep -i "Current Network"
            out = subprocess.run(
                ["system_profiler", "SPAirPortDataType"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if out.returncode != 0:
                return False
            return LAN_NETWORK_NAME.lower() in out.stdout.lower()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return False


def _is_ethernet_connected() -> bool:
    """True if primary or any active connection is Ethernet (wired)."""
    system = platform.system()
    try:
        if system == "Linux":
            # nmcli -t -f TYPE,NAME connection show --active; TYPE can be 802-3-ethernet
            out = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if out.returncode != 0:
                return False
            return "802-3-ethernet" in out.stdout.lower()
        if system == "Windows":
            # PowerShell: (Get-NetAdapter | Where-Object Status -eq Up).MediaType
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-NetAdapter | Where-Object Status -eq 'Up').MediaType"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if out.returncode != 0 or not out.stdout.strip():
                return False
            return "802.3" in out.stdout or "ethernet" in out.stdout.lower()
        if system == "Darwin":
            # system_profiler SPNetworkDataType; look for Ethernet
            out = subprocess.run(
                ["system_profiler", "SPNetworkDataType"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if out.returncode != 0:
                return False
            return "Ethernet" in out.stdout or "USB 10/100/1000" in out.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return False


def _can_reach_lan_server() -> bool:
    """True if the Brandy Box server on the Raspberry Pi is reachable at LAN_HOST:PORT."""
    url = f"http://{LAN_HOST}:{BACKEND_PORT}/api/users/me"
    try:
        with httpx.Client(timeout=LAN_REACH_TIMEOUT) as client:
            # HEAD or GET; server may require auth for /api/users/me, so use a simple endpoint if available
            r = client.get(url)
            # 401 Unauthorized still means server is reachable
            if r.status_code in (200, 401):
                return True
            # 404/405 etc. might mean wrong path but server is up
            if r.status_code < 500:
                return True
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        pass
    # Fallback: try root or health if backend has one; many backends return 404 for /
    try:
        with httpx.Client(timeout=LAN_REACH_TIMEOUT) as client:
            r = client.get(f"http://{LAN_HOST}:{BACKEND_PORT}/")
            if r.status_code < 500:
                return True
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        pass
    return False


def is_local_network() -> bool:
    """
    True if the client should use the local Raspberry Pi URL (higher performance, no Cloudflare).
    Local when: WiFi SSID is "brandstaetter", or connected via Ethernet and Pi is reachable at
    http://192.168.0.150:8081. Default is remote (returns False).
    """
    if _on_lan_brandstaetter():
        log.debug("Local network: WiFi SSID/connection is brandstaetter")
        return True
    if _is_ethernet_connected() and _can_reach_lan_server():
        log.debug("Local network: Ethernet connected and Pi reachable")
        return True
    return False


def get_base_url() -> str:
    """
    Return backend base URL. Prefer env BRANDYBOX_BASE_URL if set.
    When config is automatic: use LAN URL if is_local_network() else Cloudflare.
    When config is manual: use configured manual_base_url.
    """
    override = os.environ.get("BRANDYBOX_BASE_URL", "").strip()
    if override:
        log.info("Using base URL from BRANDYBOX_BASE_URL: %s", override.rstrip("/"))
        return override.rstrip("/")

    # Avoid circular import: config imports are done inside so network can be imported first
    from brandybox import config as app_config
    mode = app_config.get_base_url_mode()
    if mode == "manual":
        url = app_config.get_manual_base_url() or CLOUDFLARE_URL
        log.info("Using manual base URL: %s", url.rstrip("/"))
        return url.rstrip("/")

    # Automatic: default remote; use LAN only when local rules match
    if is_local_network():
        url = f"http://{LAN_HOST}:{BACKEND_PORT}"
        log.info("Automatic mode: local network, using base URL: %s", url)
        return url
    log.info("Automatic mode: remote, using Cloudflare base URL: %s", CLOUDFLARE_URL)
    return CLOUDFLARE_URL
