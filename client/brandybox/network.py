"""Resolve backend base URL: LAN (brandstaetter) vs Cloudflare."""

import platform
import re
import subprocess
from typing import Optional

# Defaults from plan
LAN_HOST = "192.168.0.150"
LAN_NETWORK_NAME = "brandstaetter"
BACKEND_PORT = "8081"
CLOUDFLARE_URL = "https://brandybox.brandstaetter.rocks"


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


def get_base_url() -> str:
    """
    Return backend base URL: http://192.168.0.150:8081 on LAN brandstaetter,
    else https://brandybox.brandstaetter.rocks (no port in URL for HTTPS).
    """
    if _on_lan_brandstaetter():
        return f"http://{LAN_HOST}:{BACKEND_PORT}"
    return CLOUDFLARE_URL
