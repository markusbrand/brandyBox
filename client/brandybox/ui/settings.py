"""Folder picker, login form, admin panel."""

import logging
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from typing import TYPE_CHECKING, Callable, List, Optional

from brandybox import config as app_config
from brandybox.network import get_base_url
from brandybox.ui.dialogs import confirm_folder_overwrite

if TYPE_CHECKING:
    from brandybox.api.client import BrandyBoxAPI

log = logging.getLogger(__name__)


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
    on_cancel: Optional[Callable[[], None]] = None,
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
    on_choose_folder: Optional[Callable[[], None]] = None,
    on_toggle_autostart: Optional[Callable[[bool], None]] = None,
    api: Optional["BrandyBoxAPI"] = None,
) -> None:
    """
    Show settings window: server URL (automatic/manual), sync folder,
    autostart, and optionally admin user management.
    If api is provided and current user is admin, show create/delete users.
    """
    root = tk.Tk()
    root.title("Brandy Box – Settings")
    root.resizable(True, True)
    root.minsize(420, 320)

    frame = ttk.Frame(root, padding=20)
    frame.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    row = 0

    # --- Server / base URL ---
    ttk.Label(frame, text="Server (base URL)", font=("", 10, "bold")).grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(0, 4)
    )
    row += 1
    url_mode_var = tk.StringVar(value=app_config.get_base_url_mode())
    manual_url_var = tk.StringVar(value=app_config.get_manual_base_url())
    current_url_label = ttk.Label(
        frame,
        text="Current: " + get_base_url(),
        wraplength=400,
        foreground="gray",
    )
    current_url_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))
    row += 1

    def _update_url_from_mode() -> None:
        if url_mode_var.get() == "manual":
            url = (manual_url_var.get() or "").strip() or app_config.DEFAULT_REMOTE_BASE_URL
            app_config.set_manual_base_url(manual_url_var.get())
        else:
            app_config.set_base_url_mode("automatic")
            url = get_base_url()
        current_url_label.config(text="Current: " + url)
        if api:
            api.set_base_url(url)

    def on_mode_change() -> None:
        mode = url_mode_var.get()
        app_config.set_base_url_mode(mode)
        manual_entry.config(state="normal" if mode == "manual" else "disabled")
        _update_url_from_mode()

    ttk.Radiobutton(
        frame,
        text="Automatic (detect local vs remote)",
        variable=url_mode_var,
        value="automatic",
        command=on_mode_change,
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 2))
    row += 1
    ttk.Radiobutton(
        frame,
        text="Manual base URL:",
        variable=url_mode_var,
        value="manual",
        command=on_mode_change,
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 2))
    row += 1
    manual_entry = ttk.Entry(frame, textvariable=manual_url_var, width=50)
    manual_entry.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    if url_mode_var.get() != "manual":
        manual_entry.config(state="disabled")
    row += 1

    def on_manual_url_change(*args: object) -> None:
        if url_mode_var.get() == "manual":
            app_config.set_manual_base_url(manual_url_var.get())
            url = app_config.get_manual_base_url()
            current_url_label.config(text="Current: " + url)
            if api:
                api.set_base_url(url)

    def _on_manual_url_trace(*args: object) -> None:
        if url_mode_var.get() == "manual":
            on_manual_url_change()

    manual_url_var.trace_add("write", _on_manual_url_trace)
    ttk.Separator(frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=(12, 12))
    row += 1

    # --- Sync folder ---
    ttk.Label(frame, text="Sync folder", font=("", 10, "bold")).grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(0, 2))
    row += 1
    sync_path = app_config.get_sync_folder_path()
    path_var = tk.StringVar(value=str(sync_path))
    path_label = ttk.Label(frame, textvariable=path_var, wraplength=400)
    path_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
    row += 1

    def _clear_folder_contents(path: Path) -> None:
        if not path.is_dir():
            return
        for child in list(path.iterdir()):
            if child.is_file():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                shutil.rmtree(child)

    def choose_folder() -> None:
        folder = filedialog.askdirectory(parent=root, title="Select folder to sync")
        if not folder:
            return
        if not confirm_folder_overwrite(root):
            log.info("User cancelled folder selection")
            return
        p = Path(folder).resolve()
        log.info("Sync folder selected: %s; clearing sync state and folder contents", p)
        app_config.clear_sync_state()
        p.mkdir(parents=True, exist_ok=True)
        _clear_folder_contents(p)
        app_config.set_sync_folder_path(p)
        path_var.set(str(p))
        log.info("Sync folder set to %s", p)
        if on_choose_folder:
            on_choose_folder()

    ttk.Button(frame, text="Choose folder…", command=choose_folder).grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(0, 16))
    row += 1

    # --- Autostart ---
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
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 12))
    row += 1

    # --- Admin: user management ---
    is_admin = False
    if api:
        try:
            me = api.me()
            is_admin = me.get("is_admin", False)
        except Exception:
            pass

    if is_admin and api:
        ttk.Separator(frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=(12, 12))
        row += 1
        ttk.Label(frame, text="User management (admin)", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1
        users_listbox_frame = ttk.Frame(frame)
        users_listbox_frame.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        row += 1
        users_listbox = tk.Listbox(users_listbox_frame, height=5, width=50)
        users_listbox.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(users_listbox_frame, orient="vertical", command=users_listbox.yview)
        scroll.pack(side="right", fill="y")
        users_listbox.config(yscrollcommand=scroll.set)
        user_data: List[dict] = []

        def refresh_users_list() -> None:
            try:
                users = api.list_users()
                user_data.clear()
                users_listbox.delete(0, tk.END)
                for u in users:
                    email = u.get("email", "")
                    user_data.append(u)
                    users_listbox.insert(tk.END, f"{email}  ({u.get('first_name', '')} {u.get('last_name', '')})")
            except Exception as e:
                messagebox.showerror("Error", f"Could not load users: {e}", parent=root)

        def create_user_dialog() -> None:
            win = tk.Toplevel(root)
            win.title("Create user")
            win.transient(root)
            win.grab_set()
            f = ttk.Frame(win, padding=16)
            f.grid(row=0, column=0, sticky="nsew")
            ttk.Label(f, text="Email").grid(row=0, column=0, sticky="w", pady=(0, 2))
            email_var = tk.StringVar()
            ttk.Entry(f, textvariable=email_var, width=36).grid(row=1, column=0, pady=(0, 8))
            ttk.Label(f, text="First name").grid(row=2, column=0, sticky="w", pady=(0, 2))
            first_var = tk.StringVar()
            ttk.Entry(f, textvariable=first_var, width=36).grid(row=3, column=0, pady=(0, 8))
            ttk.Label(f, text="Last name").grid(row=4, column=0, sticky="w", pady=(0, 2))
            last_var = tk.StringVar()
            ttk.Entry(f, textvariable=last_var, width=36).grid(row=5, column=0, pady=(0, 12))

            def do_create() -> None:
                email = email_var.get().strip()
                first = first_var.get().strip()
                last = last_var.get().strip()
                if not email:
                    messagebox.showerror("Error", "Enter email.", parent=win)
                    return
                if not first:
                    messagebox.showerror("Error", "Enter first name.", parent=win)
                    return
                if not last:
                    messagebox.showerror("Error", "Enter last name.", parent=win)
                    return
                try:
                    api.create_user(email, first, last)
                    messagebox.showinfo("Created", "User created. Password will be sent by email.", parent=win)
                    win.destroy()
                    refresh_users_list()
                except Exception as e:
                    msg = str(e)
                    try:
                        from httpx import HTTPStatusError
                        if isinstance(e, HTTPStatusError) and e.response is not None:
                            try:
                                msg = e.response.json().get("detail", msg)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    messagebox.showerror("Error", msg, parent=win)

            ttk.Button(f, text="Create", command=do_create).grid(row=6, column=0, pady=(0, 4))
            ttk.Button(f, text="Cancel", command=win.destroy).grid(row=7, column=0)

        def delete_selected_user() -> None:
            sel = users_listbox.curselection()
            if not sel:
                messagebox.showinfo("Info", "Select a user to delete.", parent=root)
                return
            idx = int(sel[0])
            if idx >= len(user_data):
                return
            u = user_data[idx]
            email = u.get("email", "")
            if not messagebox.askyesno("Confirm", f"Delete user {email}?", parent=root, icon="warning"):
                return
            try:
                api.delete_user(email)
                messagebox.showinfo("Done", "User deleted.", parent=root)
                refresh_users_list()
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete user: {e}", parent=root)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1
        ttk.Button(btn_frame, text="Refresh list", command=refresh_users_list).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Create user…", command=create_user_dialog).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Delete selected", command=delete_selected_user).pack(side="left")
        refresh_users_list()

    def on_close() -> None:
        if not app_config.user_has_set_sync_folder():
            try:
                app_config.set_sync_folder_path(Path(path_var.get()).resolve())
            except (OSError, ValueError):
                pass
        root.destroy()

    ttk.Button(frame, text="Close", command=on_close).grid(row=row, column=0, sticky="w", pady=(12, 0))
    row += 1

    frame.rowconfigure(0, weight=0)
    root.update_idletasks()
    _center(root)
    root.mainloop()


