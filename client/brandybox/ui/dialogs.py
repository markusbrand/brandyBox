"""Warning dialogs (e.g. folder will be cleared)."""

import tkinter as tk
from tkinter import messagebox
from typing import Optional


def confirm_folder_overwrite(parent: Optional[tk.Tk] = None) -> bool:
    """
    Show warning that the chosen folder will be cleared and then synced from the server.
    Returns True if user confirms, False otherwise.
    """
    root = parent or tk.Tk()
    root.withdraw()
    result = messagebox.askyesno(
        "Confirm sync folder",
        "All files and folders in the selected directory will be deleted. "
        "Then the folder will be filled with the contents from the server. Continue?",
        icon=messagebox.WARNING,
        parent=root,
    )
    if not parent:
        root.destroy()
    return result
