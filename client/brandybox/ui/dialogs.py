"""Warning dialogs (e.g. folder will be cleared)."""

import tkinter as tk
from tkinter import messagebox
from typing import Optional


def confirm_folder_overwrite(parent: Optional[tk.Tk] = None) -> bool:
    """
    Show warning that the chosen folder may be cleared/replaced for sync.
    Returns True if user confirms, False otherwise.
    """
    root = parent or tk.Tk()
    root.withdraw()
    result = messagebox.askyesno(
        "Confirm sync folder",
        "Everything in the selected folder will be synchronized with Brandy Box. "
        "Existing files may be replaced or removed to match the server. Continue?",
        icon=messagebox.WARNING,
        parent=root,
    )
    if not parent:
        root.destroy()
    return result
