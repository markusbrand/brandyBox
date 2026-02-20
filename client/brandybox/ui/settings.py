"""Folder picker, login form, admin panel.

Modern flat UI: clear hierarchy, consistent spacing, primary/secondary actions.
Uses a clean sans-serif font and flat buttons (no scrollbar, no legacy 3D look).
"""

import logging
import shutil
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont, ttk, filedialog, messagebox
from typing import TYPE_CHECKING, Callable, List, Optional

from brandybox import config as app_config
from brandybox.network import get_base_url
from brandybox.ui.dialogs import confirm_folder_overwrite

if TYPE_CHECKING:
    from brandybox.api.client import BrandyBoxAPI

log = logging.getLogger(__name__)

# When showing Settings as a Toplevel (parent is not None), reuse one window: raise if already open.
_current_settings_window: Optional[tk.Toplevel] = None

# Spacing (logical pixels)
PAD_WINDOW = 24
PAD_SECTION = 20
PAD_ROW = 8

# Modern sans-serif (widely available per platform)
def _font_family() -> str:
    if sys.platform == "win32":
        return "Segoe UI"
    if sys.platform == "darwin":
        return "SF Pro Text"
    # Linux: Liberation Sans is in most distros; DejaVu Sans and Ubuntu are common
    return "Liberation Sans"

FONT_FAMILY = _font_family()
FONT_SIZE = 11
FONT_SIZE_TITLE = 13
FONT_SIZE_CAPTION = 10

# Colors
COLOR_PRIMARY = "#1a73e8"
COLOR_PRIMARY_HOVER = "#1557b0"
COLOR_SURFACE = "#ffffff"
COLOR_BACKGROUND = "#f5f5f5"
COLOR_ON_SURFACE = "#202124"
COLOR_ON_SURFACE_VARIANT = "#5f6368"
COLOR_OUTLINE = "#e0e0e0"
COLOR_BTN_SECONDARY_BG = "#e8eaed"
COLOR_BTN_SECONDARY_FG = "#202124"
BTN_RADIUS = 8  # rounded corner radius (pixels)


def _rounded_rect(canvas: tk.Canvas, x0: int, y0: int, x1: int, y1: int, r: int, **kw: object) -> None:
    """Draw a rounded rectangle on canvas (Google/Apple style)."""
    if r <= 0:
        canvas.create_rectangle(x0, y0, x1, y1, **kw)
        return
    # Corners (arcs), then edges (rectangles)
    canvas.create_arc(x0, y0, x0 + 2 * r, y0 + 2 * r, start=90, extent=90, style=tk.PIESLICE, **kw)
    canvas.create_arc(x1 - 2 * r, y0, x1, y0 + 2 * r, start=0, extent=90, style=tk.PIESLICE, **kw)
    canvas.create_arc(x1 - 2 * r, y1 - 2 * r, x1, y1, start=270, extent=90, style=tk.PIESLICE, **kw)
    canvas.create_arc(x0, y1 - 2 * r, x0 + 2 * r, y1, start=180, extent=90, style=tk.PIESLICE, **kw)
    canvas.create_rectangle(x0 + r, y0, x1 - r, y1, **kw)
    canvas.create_rectangle(x0, y0 + r, x0 + r, y1 - r, **kw)
    canvas.create_rectangle(x1 - r, y0 + r, x1, y1 - r, **kw)


def _apply_theme(root: tk.Tk | tk.Toplevel) -> None:
    """Apply flat, modern ttk theme and fonts."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "TFrame",
        background=COLOR_SURFACE,
    )
    style.configure(
        "TLabel",
        background=COLOR_SURFACE,
        foreground=COLOR_ON_SURFACE,
        font=(FONT_FAMILY, FONT_SIZE),
    )
    style.configure(
        "Title.TLabel",
        background=COLOR_SURFACE,
        foreground=COLOR_ON_SURFACE,
        font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
    )
    style.configure(
        "Caption.TLabel",
        background=COLOR_SURFACE,
        foreground=COLOR_ON_SURFACE_VARIANT,
        font=(FONT_FAMILY, FONT_SIZE_CAPTION),
    )
    style.configure(
        "TEntry",
        fieldbackground=COLOR_SURFACE,
        foreground=COLOR_ON_SURFACE,
        font=(FONT_FAMILY, FONT_SIZE),
        padding=10,
    )
    style.configure(
        "TRadiobutton",
        background=COLOR_SURFACE,
        foreground=COLOR_ON_SURFACE,
        font=(FONT_FAMILY, FONT_SIZE),
    )
    style.configure(
        "TCheckbutton",
        background=COLOR_SURFACE,
        foreground=COLOR_ON_SURFACE,
        font=(FONT_FAMILY, FONT_SIZE),
    )
    # Modern thin scrollbar (Apple/Google style)
    try:
        style.configure(
            "Vertical.TScrollbar",
            background=COLOR_OUTLINE,
            troughcolor=COLOR_BACKGROUND,
            darkcolor=COLOR_OUTLINE,
            lightcolor=COLOR_OUTLINE,
            bordercolor=COLOR_SURFACE,
            arrowcolor=COLOR_ON_SURFACE_VARIANT,
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=COLOR_OUTLINE,
            troughcolor=COLOR_BACKGROUND,
            darkcolor=COLOR_OUTLINE,
            lightcolor=COLOR_OUTLINE,
            bordercolor=COLOR_SURFACE,
            arrowcolor=COLOR_ON_SURFACE_VARIANT,
        )
    except tk.TclError:
        pass
    if hasattr(root, "configure"):
        root.configure(bg=COLOR_SURFACE)


def _rounded_btn(
    parent: tk.Widget,
    text: str,
    command: Callable[[], None],
    primary: bool,
    **pack_kw: object,
) -> tk.Frame:
    """Rounded button (Google/Apple style). Returns the frame for pack/grid."""
    bg = COLOR_PRIMARY if primary else COLOR_BTN_SECONDARY_BG
    fg = COLOR_SURFACE if primary else COLOR_BTN_SECONDARY_FG
    hover_bg = COLOR_PRIMARY_HOVER if primary else COLOR_OUTLINE
    font_tuple = (FONT_FAMILY, FONT_SIZE, "bold") if primary else (FONT_FAMILY, FONT_SIZE)
    padx, pady = (24, 12) if primary else (20, 10)

    frame = tk.Frame(parent, bg=COLOR_SURFACE)

    # Width from text so label is never cut; minimum for short labels
    try:
        font_obj = tkfont.Font(font=font_tuple)
        text_w = font_obj.measure(text) + (padx * 2)
    except (tk.TclError, TypeError):
        text_w = 0
    min_w = 140 if primary else 120
    w = max(min_w, text_w)
    h = 42 if primary else 38
    canvas = tk.Canvas(
        frame,
        width=w,
        height=h,
        highlightthickness=0,
        bg=frame.cget("bg"),
        takefocus=1,
    )
    canvas.pack(fill=tk.BOTH, expand=True)

    def on_key_activate(_e: tk.Event) -> None:
        command()

    def draw(highlight: bool = False) -> None:
        canvas.delete("all")
        fill = hover_bg if highlight else bg
        _rounded_rect(canvas, 0, 0, w, h, BTN_RADIUS, fill=fill, outline=fill)
        canvas.create_text(
            w // 2, h // 2,
            text=text,
            fill=fg,
            font=font_tuple,
        )

    def on_enter(_e: tk.Event) -> None:
        draw(highlight=True)

    def on_leave(_e: tk.Event) -> None:
        draw(highlight=False)

    def on_click(_e: tk.Event) -> None:
        command()

    draw()
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    canvas.bind("<Button-1>", on_click)
    canvas.bind("<Return>", on_key_activate)
    canvas.bind("<KP_Enter>", on_key_activate)
    canvas.configure(cursor="hand2")
    if pack_kw:
        frame.pack(**pack_kw)
    return frame


def _primary_btn(
    parent: tk.Widget,
    text: str,
    command: Callable[[], None],
    **pack_kw: object,
) -> tk.Frame:
    """Rounded primary (filled) button."""
    return _rounded_btn(parent, text, command, primary=True, **pack_kw)


def _secondary_btn(
    parent: tk.Widget,
    text: str,
    command: Callable[[], None],
    **pack_kw: object,
) -> tk.Frame:
    """Rounded secondary button."""
    return _rounded_btn(parent, text, command, primary=False, **pack_kw)


def _section(parent: tk.Widget, title: str, row: int) -> tuple[ttk.Frame, int]:
    """Create a section block with title. Returns (content frame, start row inside section)."""
    container = ttk.Frame(parent)
    container.grid(row=row, column=0, sticky="ew")
    parent.columnconfigure(0, weight=1)
    lbl = ttk.Label(container, text=title, style="Title.TLabel")
    lbl.grid(row=0, column=0, sticky="w", pady=(0, PAD_ROW))
    content = ttk.Frame(container, padding=(0, 0, 0, PAD_SECTION))
    content.grid(row=1, column=0, sticky="ew")
    content.columnconfigure(0, weight=1)
    return content, 0


def _center(win: tk.Tk | tk.Toplevel) -> None:
    """Center window on screen."""
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = max(0, (win.winfo_screenheight() // 2) - (h // 2))
    win.geometry(f"+{x}+{y}")


# Margin from screen edge when placing window near tray (first start)
_TRAY_ANCHOR_MARGIN = 16


def _position_near_tray(win: tk.Tk | tk.Toplevel) -> None:
    """Place window as close as possible to the tray (top-right) while staying on-screen.
    Used on first start before the user has moved the window; tray is usually top-right
    (Linux/macOS) or bottom-right (Windows). We use top-right so the window appears
    just below/left of the tray and clamp to the visible area.
    """
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    # Anchor near top-right (tray area)
    x = sw - w - _TRAY_ANCHOR_MARGIN
    y = _TRAY_ANCHOR_MARGIN
    # Clamp so the whole window stays within the visible screen
    x = max(0, min(x, sw - w))
    y = max(0, min(y, sh - h))
    win.geometry(f"+{x}+{y}")


def ask_directory(
    parent: tk.Tk | tk.Toplevel,
    title: str = "Select folder",
    initialdir: Optional[str] = None,
) -> Optional[str]:
    """
    Custom folder picker: hidden files are hidden by default; checkbox to show them.
    Returns the selected directory path or None if cancelled.
    """
    result: List[Optional[str]] = [None]
    current = Path(initialdir or ".").resolve()
    if not current.is_dir():
        current = Path.home()

    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.transient(parent)
    dlg.resizable(True, True)
    dlg.configure(bg=COLOR_SURFACE)
    _apply_theme(dlg)
    dlg.minsize(420, 380)

    main = ttk.Frame(dlg, padding=PAD_WINDOW)
    main.grid(row=0, column=0, sticky="nsew")
    dlg.columnconfigure(0, weight=1)
    dlg.rowconfigure(0, weight=1)
    main.columnconfigure(0, weight=1)
    main.rowconfigure(2, weight=1)

    path_var = tk.StringVar(value=str(current))
    show_hidden_var = tk.BooleanVar(value=False)

    def list_entries() -> List[str]:
        try:
            entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return []
        out: List[str] = []
        for p in entries:
            if p.name.startswith(".") and not show_hidden_var.get():
                continue
            out.append(p.name + ("/" if p.is_dir() else ""))
        return out

    def refresh_list() -> None:
        lb.delete(0, tk.END)
        if current.parent != current:
            lb.insert(tk.END, "../")
        for name in list_entries():
            lb.insert(tk.END, name)
        path_var.set(str(current))

    def go_up() -> None:
        nonlocal current
        if current.parent != current:
            current = current.parent
            refresh_list()

    def on_double_click(event: tk.Event) -> None:
        nonlocal current
        sel = lb.curselection()
        if not sel:
            return
        name = lb.get(sel[0]).rstrip("/")
        if name == "..":
            go_up()
            return
        child = current / name
        if child.is_dir():
            current = child
            refresh_list()
        else:
            # could select folder and click "Select folder" – we only allow selecting dirs
            pass

    def on_show_hidden_change() -> None:
        refresh_list()

    def select_here() -> None:
        result[0] = str(current)
        dlg.destroy()

    def cancel() -> None:
        dlg.destroy()

    ttk.Label(main, text="Current folder:", style="Caption.TLabel").grid(
        row=0, column=0, sticky="w", pady=(0, 2)
    )
    path_label = ttk.Label(main, textvariable=path_var, wraplength=400)
    path_label.grid(row=1, column=0, sticky="w", pady=(0, PAD_ROW))
    main.columnconfigure(0, weight=1)

    lb_frame = ttk.Frame(main)
    lb_frame.grid(row=2, column=0, sticky="nsew", pady=(0, PAD_ROW))
    lb_frame.columnconfigure(0, weight=1)
    lb_frame.rowconfigure(0, weight=1)
    lb = tk.Listbox(
        lb_frame,
        height=12,
        font=(FONT_FAMILY, FONT_SIZE),
        bg=COLOR_SURFACE,
        fg=COLOR_ON_SURFACE,
        selectbackground=COLOR_PRIMARY,
        selectforeground=COLOR_SURFACE,
        highlightthickness=0,
    )
    lb.grid(row=0, column=0, sticky="nsew")
    lb.bind("<Double-Button-1>", on_double_click)
    scroll = ttk.Scrollbar(lb_frame, orient="vertical", command=lb.yview)
    scroll.grid(row=0, column=1, sticky="ns")
    lb.configure(yscrollcommand=scroll.set)

    cb = ttk.Checkbutton(
        main,
        text="Show hidden files",
        variable=show_hidden_var,
        command=on_show_hidden_change,
    )
    cb.grid(row=3, column=0, sticky="w", pady=(PAD_ROW, PAD_SECTION))

    btn_f = ttk.Frame(main)
    btn_f.grid(row=4, column=0, sticky="w")
    _primary_btn(btn_f, "Select folder", select_here, side="left", padx=(0, PAD_ROW))
    _secondary_btn(btn_f, "Cancel", cancel, side="left")

    refresh_list()
    _center(dlg)
    dlg.update_idletasks()
    # Defer grab until window is viewable (fixes "grab failed: window not viewable" on some WMs)
    def set_grab() -> None:
        try:
            dlg.grab_set()
        except tk.TclError:
            pass

    dlg.after(50, set_grab)
    dlg.wait_window()
    return result[0]


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
    root.configure(bg=COLOR_SURFACE)
    _apply_theme(root)

    main = ttk.Frame(root, padding=PAD_WINDOW)
    main.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    ttk.Label(main, text="Email", style="Caption.TLabel").grid(
        row=0, column=0, sticky="w", pady=(0, 2)
    )
    email_var = tk.StringVar()
    email_entry = ttk.Entry(main, textvariable=email_var, width=40)
    email_entry.grid(row=1, column=0, sticky="ew", pady=(0, PAD_ROW))

    ttk.Label(main, text="Password", style="Caption.TLabel").grid(
        row=2, column=0, sticky="w", pady=(PAD_ROW, 2)
    )
    password_var = tk.StringVar()
    password_entry = ttk.Entry(main, textvariable=password_var, show="*", width=40)
    password_entry.grid(row=3, column=0, sticky="ew", pady=(0, PAD_SECTION))

    def _on_return_login(_e: tk.Event) -> None:
        do_login()

    email_entry.bind("<Return>", _on_return_login)
    email_entry.bind("<KP_Enter>", _on_return_login)
    password_entry.bind("<Return>", _on_return_login)
    password_entry.bind("<KP_Enter>", _on_return_login)

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

    btn_frame = ttk.Frame(main)
    btn_frame.grid(row=4, column=0, sticky="w", pady=(0, 0))
    _primary_btn(btn_frame, "Login", do_login, side="left", padx=(0, PAD_ROW))
    _secondary_btn(btn_frame, "Cancel", do_cancel, side="left")

    main.columnconfigure(0, weight=1)
    root.update_idletasks()
    _center(root)
    email_entry.focus_set()
    root.mainloop()


def show_settings(
    on_choose_folder: Optional[Callable[[], None]] = None,
    on_toggle_autostart: Optional[Callable[[bool], None]] = None,
    api: Optional["BrandyBoxAPI"] = None,
    parent: Optional[tk.Tk] = None,
    on_logout: Optional[Callable[[], None]] = None,
) -> None:
    """
    Show settings window: server URL (automatic/manual), sync folder,
    autostart, and optionally admin user management.
    If api is provided and current user is admin, show create/delete users.
    When parent is given (e.g. from tray), settings opens as a Toplevel so
    it can be closed and reopened; only one Settings window is shown at a time
    (re-opening raises and focuses the existing window). Otherwise a standalone Tk and mainloop().
    When on_logout is provided (e.g. from tray), an Account section shows
    "Log out" to sign out and switch to a different account.
    """
    global _current_settings_window
    log.info("show_settings: start parent=%s", parent is not None)
    if parent is not None:
        # Single-instance: if Settings is already open, raise and focus it instead of opening a second window.
        if _current_settings_window is not None:
            try:
                if _current_settings_window.winfo_exists():
                    _current_settings_window.lift()
                    _current_settings_window.focus_force()
                    try:
                        _current_settings_window.deiconify()
                    except tk.TclError:
                        pass
                    log.info("show_settings: raised existing Settings window")
                    return
            except tk.TclError:
                pass
            _current_settings_window = None
        # On Linux, a Toplevel of a withdrawn parent may never map. Deiconify parent
        # briefly so the Toplevel can be created, then hide parent again.
        parent.deiconify()
        parent.update_idletasks()
        log.info("show_settings: creating Toplevel")
        win = tk.Toplevel(parent)
        _current_settings_window = win
        win.withdraw()  # Keep hidden until fast UI is built (avoids incomplete window on Windows)
        # Do not use transient(parent): when parent is later withdrawn, some WMs hide transient children
        parent.withdraw()
        log.info("show_settings: Toplevel created (withdrawn until ready)")
    else:
        win = tk.Tk()
        log.info("show_settings: Tk() created")
    win.title("Brandy Box – Settings")
    win.resizable(True, True)
    win.minsize(500, 560)
    saved_geom = app_config.get_settings_window_geometry()
    if saved_geom:
        try:
            win.geometry(saved_geom)
        except tk.TclError:
            pass
    win.configure(bg=COLOR_BACKGROUND)
    _apply_theme(win)
    log.info("show_settings: theme applied")

    frame = ttk.Frame(win, padding=PAD_WINDOW)
    frame.grid(row=0, column=0, sticky="nsew")
    win.columnconfigure(0, weight=1)
    win.rowconfigure(0, weight=1)

    row = 0

    # --- Server / base URL ---
    sec, r = _section(frame, "Server", row)
    row += 2
    current_url_text = "Current: " + get_base_url()
    url_mode_var = tk.StringVar(value=app_config.get_base_url_mode())
    manual_url_var = tk.StringVar(value=app_config.get_manual_base_url())
    current_url_label = ttk.Label(sec, text=current_url_text, style="Caption.TLabel", wraplength=420)
    current_url_label.grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, PAD_ROW))
    r += 1

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
        sec,
        text="Automatic (detect local vs remote)",
        variable=url_mode_var,
        value="automatic",
        command=on_mode_change,
    ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 2))
    r += 1
    ttk.Radiobutton(
        sec,
        text="Manual base URL",
        variable=url_mode_var,
        value="manual",
        command=on_mode_change,
    ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 2))
    r += 1
    manual_entry = ttk.Entry(sec, textvariable=manual_url_var, width=52)
    manual_entry.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, PAD_ROW))
    if url_mode_var.get() != "manual":
        manual_entry.config(state="disabled")
    r += 1
    sec.columnconfigure(0, weight=1)

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

    # --- Sync folder ---
    sec2, r2 = _section(frame, "Sync folder", row)
    row += 2
    sync_path = app_config.get_sync_folder_path()
    path_var = tk.StringVar(value=str(sync_path))
    path_label = ttk.Label(sec2, textvariable=path_var, style="Caption.TLabel", wraplength=420)
    path_label.grid(row=r2, column=0, columnspan=2, sticky="w", pady=(0, PAD_ROW))
    r2 += 1

    def _clear_folder_contents(path: Path) -> None:
        if not path.is_dir():
            return
        for child in list(path.iterdir()):
            if child.is_file():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                shutil.rmtree(child)

    def choose_folder() -> None:
        folder = ask_directory(
            win,
            title="Select folder to sync",
            initialdir=str(Path.home()),
        )
        if not folder:
            return
        if not confirm_folder_overwrite(win):
            log.info("User cancelled folder selection")
            return
        p = Path(folder).resolve()
        log.info("Sync folder selected: %s; clearing sync state and folder contents", p)
        app_config.clear_sync_state()
        p.mkdir(parents=True, exist_ok=True)
        _clear_folder_contents(p)
        app_config.set_sync_folder_path(p)
        path_var.set(str(p))
        win.update_idletasks()  # ensure path label refreshes
        log.info("Sync folder set to %s", p)
        if on_choose_folder:
            on_choose_folder()

    choose_btn = _secondary_btn(sec2, "Choose folder…", choose_folder)
    choose_btn.grid(row=r2, column=0, columnspan=2, sticky="w", pady=(0, 0))
    sec2.columnconfigure(0, weight=1)
    log.info("show_settings: sync folder section done")

    # --- Autostart ---
    sec3, r3 = _section(frame, "Startup", row)
    row += 2
    autostart_var = tk.BooleanVar(value=app_config.get_autostart())

    def on_autostart_change() -> None:
        app_config.set_autostart(autostart_var.get())
        if on_toggle_autostart:
            on_toggle_autostart(autostart_var.get())

    ttk.Checkbutton(
        sec3,
        text="Start Brandy Box when I log in",
        variable=autostart_var,
        command=on_autostart_change,
    ).grid(row=r3, column=0, columnspan=2, sticky="w", pady=(0, 0))
    sec3.columnconfigure(0, weight=1)

    # --- Change password (any logged-in user) ---
    if api:
        sec4, r4 = _section(frame, "Account", row)
        row += 2

        def change_password_dialog() -> None:
            dlg = tk.Toplevel(win)
            dlg.title("Change password")
            dlg.transient(win)
            dlg.resizable(False, False)
            dlg.minsize(400, 380)
            dlg.geometry("400x380")
            dlg.configure(bg=COLOR_SURFACE)
            _apply_theme(dlg)
            f = ttk.Frame(dlg, padding=PAD_WINDOW)
            f.grid(row=0, column=0, sticky="nsew")
            dlg.columnconfigure(0, weight=1)
            dlg.rowconfigure(0, weight=1)
            r = 0
            ttk.Label(f, text="Current password", style="Caption.TLabel").grid(
                row=r, column=0, sticky="w", pady=(0, 2)
            )
            r += 1
            current_var = tk.StringVar()
            current_entry = ttk.Entry(f, textvariable=current_var, show="*", width=38)
            current_entry.grid(row=r, column=0, sticky="ew", pady=(0, PAD_ROW))
            r += 1
            ttk.Label(f, text="New password", style="Caption.TLabel").grid(
                row=r, column=0, sticky="w", pady=(PAD_ROW, 2)
            )
            r += 1
            new_var = tk.StringVar()
            new_entry = ttk.Entry(f, textvariable=new_var, show="*", width=38)
            new_entry.grid(row=r, column=0, sticky="ew", pady=(0, PAD_ROW))
            r += 1
            ttk.Label(f, text="Confirm new password", style="Caption.TLabel").grid(
                row=r, column=0, sticky="w", pady=(PAD_ROW, 2)
            )
            r += 1
            confirm_var = tk.StringVar()
            confirm_entry = ttk.Entry(f, textvariable=confirm_var, show="*", width=38)
            confirm_entry.grid(row=r, column=0, sticky="ew", pady=(0, PAD_SECTION))
            r += 1

            def do_change() -> None:
                current = current_var.get()
                new = new_entry.get()
                confirm = confirm_entry.get()
                if not current:
                    messagebox.showerror("Error", "Enter your current password.", parent=dlg)
                    return
                if not new:
                    messagebox.showerror("Error", "Enter a new password.", parent=dlg)
                    return
                if new != confirm:
                    messagebox.showerror(
                        "Error", "New password and confirmation do not match.", parent=dlg
                    )
                    return
                if len(new) < 8:
                    messagebox.showerror(
                        "Error", "New password must be at least 8 characters.", parent=dlg
                    )
                    return
                try:
                    api.change_password(current, new)
                    messagebox.showinfo("Done", "Password updated successfully.", parent=dlg)
                    dlg.destroy()
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
                    messagebox.showerror("Error", msg, parent=dlg)

            btn_f = ttk.Frame(f)
            btn_f.grid(row=r, column=0, sticky="w", pady=(PAD_ROW, 0))
            _primary_btn(btn_f, "Change password", do_change, side="left", padx=(0, PAD_ROW))
            _secondary_btn(btn_f, "Cancel", dlg.destroy, side="left")
            f.columnconfigure(0, weight=1)
            dlg.update_idletasks()
            _center(dlg)

            def set_grab_chpwd() -> None:
                try:
                    dlg.grab_set()
                except tk.TclError:
                    pass

            dlg.after(50, set_grab_chpwd)

        chpwd_btn = _secondary_btn(sec4, "Change password…", change_password_dialog)
        chpwd_btn.grid(row=r4, column=0, columnspan=2, sticky="w", pady=(0, PAD_ROW))
        r4 += 1
        sec4.columnconfigure(0, weight=1)

        if on_logout:

            def do_logout() -> None:
                if messagebox.askyesno(
                    "Log out",
                    "Log out and sign in with a different account?",
                    parent=win,
                    icon="question",
                ):
                    win.destroy()
                    on_logout()

            logout_btn = _secondary_btn(sec4, "Log out / Switch account", do_logout)
            logout_btn.grid(row=r4, column=0, columnspan=2, sticky="w", pady=(0, 0))
            sec4.columnconfigure(0, weight=1)

    # --- Admin: user management (deferred so window shows quickly; avoids blocking on api.me/list_users) ---
    admin_sec: Optional[ttk.Frame] = None
    if api:
        sec5, r5 = _section(frame, "User management (admin)", row)
        row += 2
        admin_sec = sec5
        admin_placeholder = ttk.Label(sec5, text="Loading…", style="Caption.TLabel")
        admin_placeholder.grid(row=0, column=0, sticky="w", pady=(0, PAD_ROW))
        sec5.columnconfigure(0, weight=1)

    def _load_admin_section_async() -> None:
        """Run after window is shown: fetch is_admin and either show list or 'Only for administrators'."""
        if not api or admin_sec is None:
            return
        # Remove placeholder
        for w in admin_sec.grid_slaves():
            w.destroy()
        is_admin = False
        try:
            me = api.me()
            is_admin = me.get("is_admin", me.get("isAdmin", False))
            log.info("show_settings: me is_admin=%s (deferred)", is_admin)
        except Exception as e:
            log.warning("show_settings: could not fetch /me for admin check: %s", e)
        if not is_admin:
            ttk.Label(
                admin_sec, text="Only for administrators.", style="Caption.TLabel"
            ).grid(row=0, column=0, sticky="w", pady=(0, PAD_ROW))
            return
        r5 = 0
        users_listbox_frame = ttk.Frame(admin_sec)
        users_listbox_frame.grid(row=r5, column=0, columnspan=2, sticky="nsew", pady=(0, PAD_ROW))
        r5 += 1
        users_listbox = tk.Listbox(
            users_listbox_frame,
            height=5,
            width=52,
            bg=COLOR_SURFACE,
            fg=COLOR_ON_SURFACE,
            selectbackground=COLOR_PRIMARY,
            selectforeground=COLOR_SURFACE,
            font=(FONT_FAMILY, FONT_SIZE),
            highlightthickness=0,
        )
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
                    users_listbox.insert(
                        tk.END, f"{email}  ({u.get('first_name', '')} {u.get('last_name', '')})"
                    )
            except Exception as e:
                messagebox.showerror("Error", f"Could not load users: {e}", parent=win)

        def create_user_dialog() -> None:
            dlg = tk.Toplevel(win)
            dlg.title("Create user")
            dlg.transient(win)
            dlg.resizable(False, False)
            dlg.minsize(380, 320)
            dlg.geometry("380x320")
            dlg.configure(bg=COLOR_SURFACE)
            _apply_theme(dlg)
            f = ttk.Frame(dlg, padding=PAD_WINDOW)
            f.grid(row=0, column=0, sticky="nsew")
            dlg.columnconfigure(0, weight=1)
            dlg.rowconfigure(0, weight=1)
            r = 0
            ttk.Label(f, text="Email", style="Caption.TLabel").grid(row=r, column=0, sticky="w", pady=(0, 2))
            r += 1
            email_var = tk.StringVar()
            email_entry = ttk.Entry(f, textvariable=email_var, width=38)
            email_entry.grid(row=r, column=0, sticky="ew", pady=(0, PAD_ROW))
            r += 1
            ttk.Label(f, text="First name", style="Caption.TLabel").grid(row=r, column=0, sticky="w", pady=(PAD_ROW, 2))
            r += 1
            first_var = tk.StringVar()
            first_entry = ttk.Entry(f, textvariable=first_var, width=38)
            first_entry.grid(row=r, column=0, sticky="ew", pady=(0, PAD_ROW))
            r += 1
            ttk.Label(f, text="Last name", style="Caption.TLabel").grid(row=r, column=0, sticky="w", pady=(PAD_ROW, 2))
            r += 1
            last_var = tk.StringVar()
            last_entry = ttk.Entry(f, textvariable=last_var, width=38)
            last_entry.grid(row=r, column=0, sticky="ew", pady=(0, PAD_SECTION))
            r += 1

            def do_create() -> None:
                email = email_entry.get().strip()
                first = first_entry.get().strip()
                last = last_entry.get().strip()
                if not email:
                    messagebox.showerror("Error", "Enter email.", parent=dlg)
                    return
                if not first:
                    messagebox.showerror("Error", "Enter first name.", parent=dlg)
                    return
                if not last:
                    messagebox.showerror("Error", "Enter last name.", parent=dlg)
                    return
                try:
                    api.create_user(email, first, last)
                    messagebox.showinfo(
                        "Created", "User created. Password will be sent by email.", parent=dlg
                    )
                    dlg.destroy()
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
                    messagebox.showerror("Error", msg, parent=dlg)

            btn_f = ttk.Frame(f)
            btn_f.grid(row=r, column=0, sticky="w", pady=(PAD_ROW, 0))
            _primary_btn(btn_f, "Create", do_create, side="left", padx=(0, PAD_ROW))
            _secondary_btn(btn_f, "Cancel", dlg.destroy, side="left")
            f.columnconfigure(0, weight=1)
            dlg.update_idletasks()
            _center(dlg)

            def set_grab_create() -> None:
                try:
                    dlg.grab_set()
                except tk.TclError:
                    pass

            dlg.after(50, set_grab_create)

        def delete_selected_user() -> None:
            sel = users_listbox.curselection()
            if not sel:
                messagebox.showinfo("Info", "Select a user to delete.", parent=win)
                return
            idx = int(sel[0])
            if idx >= len(user_data):
                return
            u = user_data[idx]
            email = u.get("email", "")
            if not messagebox.askyesno("Confirm", f"Delete user {email}?", parent=win, icon="warning"):
                return
            try:
                api.delete_user(email)
                messagebox.showinfo("Done", "User deleted.", parent=win)
                refresh_users_list()
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete user: {e}", parent=win)

        btn_frame = ttk.Frame(admin_sec)
        btn_frame.grid(row=r5, column=0, columnspan=2, sticky="w", pady=(0, 0))
        _secondary_btn(btn_frame, "Refresh list", refresh_users_list, side="left", padx=(0, PAD_ROW))
        _primary_btn(btn_frame, "Create user…", create_user_dialog, side="left", padx=(0, PAD_ROW))
        _secondary_btn(btn_frame, "Delete selected", delete_selected_user, side="left")
        admin_sec.columnconfigure(0, weight=1)
        refresh_users_list()

    def on_close() -> None:
        global _current_settings_window
        # Do not auto-save the displayed path on close: only persist when the user clicks "Choose folder".
        # Otherwise we would persist the default ~/brandyBox (capital B) and on Linux that can be the wrong
        # folder (e.g. user's files are in ~/brandybox lowercase), causing repeated full re-downloads.
        try:
            app_config.set_settings_window_geometry(win.geometry())
        except Exception:
            pass
        if _current_settings_window is win:
            _current_settings_window = None
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_close)

    frame.columnconfigure(0, weight=1)
    log.info("show_settings: layout complete, positioning")
    win.update_idletasks()
    if not saved_geom:
        _position_near_tray(win)
    if parent is not None:
        win.deiconify()
        win.lift()
        win.focus_force()
        win.update()  # force map and draw so window is visible
        log.info(
            "show_settings: done (toplevel) viewable=%s mapped=%s",
            win.winfo_viewable(),
            win.winfo_ismapped(),
        )
        if api and admin_sec is not None:
            win.after(0, _load_admin_section_async)
    else:
        log.info("show_settings: entering mainloop")
    if parent is None and api and admin_sec is not None:
        win.after(0, _load_admin_section_async)
    if parent is None:
        win.mainloop()
