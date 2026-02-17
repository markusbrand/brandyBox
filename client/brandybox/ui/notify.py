"""Desktop notifications (system tray / OS notification center).

Uses platform-native tools: notify-send (Linux), osascript (macOS), PowerShell (Windows).
No extra dependencies; fails silently if the tool is unavailable.
"""

import logging
import subprocess
import sys

log = logging.getLogger(__name__)


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
            subprocess.run(
                ["notify-send", "-u", "critical", "-a", "Brandy Box", title, body],
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
