"""Folder picker, login form, admin panel."""

import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Optional

from brandybox import config as app_config
from brandybox.ui.dialogs import confirm_folder_overwrite


def _center(win: tk.Tk) -> None:
    """Center window on screen."""
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"+{x}+{y}")


def show_login(
    on_success: Callable[[str, str], None],
    on_cancel: Optional[Callable[[], None]]] = None,
) -> None:
    """
    Show login window: email, password, Login. on_success(email, password) called on OK.
    """
    root = tk.Tk()
    root.title("Brandy Box – Login")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=20)
    frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frame, text="Email").grid(row=0, column=0, sticky="w", pady=(0, 2))
    email_var = tk.StringVar()
    email_entry = ttk.Entry(frame, textvariable=email_var, width=40)
    email_entry.grid(row=1, column=0, pady=(0, 12))

    ttk.Label(frame, text="Password").grid(row=2, column=0, sticky="w", pady=(0, 2))
    password_var = tk.StringVar()
    password_entry = ttk.Entry(frame, textvariable=password_var, show="*", width=40)
    password_entry.grid(row=3, column=0, pady=(0, 16))

    def do_login() -> None:
        email = email_var.get().strip()
        password = password_var.get()
        if not email:
            messagebox.showerror("Error", "Please enter your email.", parent=root)
            return
        if not password:
            messagebox.showerror("Error", "Please enter your password.", parent=root)
            return
        root.destroy()
        on_success(email, password)

    def do_cancel() -> None:
        root.destroy()
        if on_cancel:
            on_cancel()

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=4, column=0, pady=(0, 0))
    ttk.Button(btn_frame, text="Login", command=do_login).pack(side="left", padx=(0, 8))
    ttk.Button(btn_frame, text="Cancel", command=do_cancel).pack(side="left")

    root.update_idletasks()
    _center(root)
    root.mainloop()


def show_settings(
    on_choose_folder: Optional[Callable[[], None]]] = None,
    on_toggle_autostart: Optional[Callable[[bool], None]]] = None,
) -> None:
    """
    Show settings window: current sync folder, button to choose folder,
    autostart checkbox. Callbacks are optional.
    """
    root = tk.Tk()
    root.title("Brandy Box – Settings")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=20)
    frame.grid(row=0, column=0, sticky="nsew")

    # Sync folder
    ttk.Label(frame, text="Sync folder").grid(row=0, column=0, sticky="w", pady=(0, 2))
    sync_path = app_config.get_sync_folder_path()
    path_var = tk.StringVar(value=str(sync_path) if sync_path else "Not set")
    path_label = ttk.Label(frame, textvariable=path_var, wraplength=400)
    path_label.grid(row=1, column=0, sticky="w", pady=(0, 8))

    def choose_folder() -> None:
        folder = filedialog.askdirectory(parent=root, title="Select folder to sync")
        if not folder:
            return
        if not confirm_folder_overwrite(root):
            return
        p = Path(folder)
        app_config.set_sync_folder_path(p)
        path_var.set(str(p.resolve()))
        if on_choose_folder:
            on_choose_folder()

    ttk.Button(frame, text="Choose folder…", command=choose_folder).grid(row=2, column=0, sticky="w", pady=(0, 16))

    # Autostart
    autostart_var = tk.BooleanVar(value=app_config.get_autostart())

    def on_autostart_change() -> None:
        app_config.set_autostart(autostart_var.get())
        if on_toggle_autostart:
            on_toggle_autostart(autostart_var.get())

    ttk.Checkbutton(
        frame,
        text="Start Brandy Box when I log in",
        variable=autostart_var,
        command=on_autostart_change,
    ).grid(row=3, column=0, sticky="w", pady=(0, 12))

    ttk.Button(frame, text="Close", command=root.destroy).grid(row=4, column=0, sticky="w", pady=(8, 0))

    root.update_idletasks()
    _center(root)
    root.mainloop()


