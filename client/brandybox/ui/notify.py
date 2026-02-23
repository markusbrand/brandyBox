"""Desktop notifications (system tray / OS notification center).

Uses platform-native tools: notify-send (Linux), osascript (macOS), PowerShell (Windows).
No extra dependencies; fails silently if the tool is unavailable.

On Linux (KDE Plasma): use normal urgency and an expire-time so the popup auto-dismisses
after a few seconds; Plasma ignores expire-time for "critical" urgency, which would keep
notifications on screen until manually closed. With normal + expire-time, the popup
disappears and the notification remains in the system notification history (tray).
"""

import logging
import subprocess
import sys

log = logging.getLogger(__name__)

# Popup display time in ms (e.g. 10 s). Omit transient so notification stays in tray history.
_NOTIFY_EXPIRE_MS = 10_000


def notify_error(title: str, message: str) -> None:
    """
    Show a desktop notification for an error.

    Args:
        title: Short title (e.g. "Brandy Box – Error").
        message: Error message body; may be truncated for display.
    """
    # Truncate for notification body (avoid huge tooltips)
    body = (message or "Unknown error")[:200]
    if len(message or "") > 200:
        body += "…"

    try:
        if sys.platform == "linux":
            # Use normal urgency so KDE Plasma respects --expire-time (critical ignores it).
            # Expire-time makes the popup disappear; notification stays in system tray history.
            subprocess.run(
                [
                    "notify-send",
                    "-u", "normal",
                    "-t", str(_NOTIFY_EXPIRE_MS),
                    "-a", "Brandy Box",
                    title,
                    body,
                ],
                check=False,
                timeout=5,
                capture_output=True,
            )
        elif sys.platform == "darwin":
            # Escape for AppleScript: replace \ and "
            esc = body.replace("\\", "\\\\").replace('"', '\\"')
            tit = title.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{esc}" with title "{tit}" sound name "Basso"',
                ],
                check=False,
                timeout=5,
                capture_output=True,
            )
        elif sys.platform == "win32":
            # Optional: Windows 10+ toast via PowerShell (complex escaping). Skip to avoid blocking.
            log.debug("Desktop notification skipped on Windows (use tray tooltip)")
        else:
            log.debug("Desktop notifications not implemented for %s", sys.platform)
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        log.debug("Desktop notification failed: %s", e)


def notify_sync_complete(downloaded: int, uploaded: int) -> None:
    """
    Show a desktop notification when a sync completed with downloads and/or uploads.
    Only notifies when at least one file was downloaded or uploaded.
    Downloaded: another client uploaded, so this PC received files. Uploaded: local
    files were successfully synced to the server.
    """
    if downloaded <= 0 and uploaded <= 0:
        return
    if downloaded > 0 and uploaded > 0:
        body = f"{downloaded} file(s) downloaded, {uploaded} file(s) uploaded."
    elif downloaded > 0:
        body = f"{downloaded} file(s) downloaded from server."
    else:
        body = f"{uploaded} file(s) uploaded to server."
    title = "Brandy Box – Sync complete"
    try:
        if sys.platform == "linux":
            subprocess.run(
                [
                    "notify-send",
                    "-u", "normal",
                    "-t", str(_NOTIFY_EXPIRE_MS),
                    "-a", "Brandy Box",
                    title,
                    body,
                ],
                check=False,
                timeout=5,
                capture_output=True,
            )
        elif sys.platform == "darwin":
            esc = body.replace("\\", "\\\\").replace('"', '\\"')
            tit = title.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{esc}" with title "{tit}"',
                ],
                check=False,
                timeout=5,
                capture_output=True,
            )
        elif sys.platform == "win32":
            log.debug("Sync complete notification skipped on Windows (use tray tooltip)")
        else:
            log.debug("Desktop notifications not implemented for %s", sys.platform)
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        log.debug("Desktop notification failed: %s", e)
