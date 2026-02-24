"""Folder picker, login form, admin panel.

Modern flat UI: clear hierarchy, consistent spacing, primary/secondary actions.
Uses a clean sans-serif font and flat buttons (no scrollbar, no legacy 3D look).
"""

import logging
import queue
import shutil
import sys
import threading
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


def _format_storage_bytes(n: int) -> str:
    """Format byte count as e.g. '430.5 GiB' or '1.8 TiB'."""
    if n < 0:
        return "0 B"
    if n >= 1024**4:
        return f"{n / 1024**4:.1f} TiB"
    if n >= 1024**3:
        return f"{n / 1024**3:.1f} GiB"
    if n >= 1024**2:
        return f"{n / 1024**2:.1f} MiB"
    if n >= 1024:
        return f"{n / 1024:.1f} KiB"
    return f"{n} B"

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
COLOR_CARD = "#f0f0f0"  # light grey section cards (rounded, slightly raised)
BTN_RADIUS = 8  # rounded corner radius (pixels)
CARD_RADIUS = 12  # section card corner radius


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
    style.configure("Card.TFrame", background=COLOR_CARD)
    style.configure(
        "Card.TLabel",
        background=COLOR_CARD,
        foreground=COLOR_ON_SURFACE,
        font=(FONT_FAMILY, FONT_SIZE),
    )
    style.configure(
        "Card.Title.TLabel",
        background=COLOR_CARD,
        foreground=COLOR_ON_SURFACE,
        font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
    )
    style.configure(
        "Card.Caption.TLabel",
        background=COLOR_CARD,
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
        "Card.TRadiobutton",
        background=COLOR_CARD,
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


def _section_card(parent: tk.Widget, title: str, row: int) -> tuple[tk.Frame, int, tk.Frame]:
    """Create a section inside a light grey rounded card. Returns (content frame, start row, outer frame)."""
    outer = tk.Frame(parent, bg=COLOR_SURFACE)
    outer.grid(row=row, column=0, sticky="ew", pady=(0, 6))
    parent.columnconfigure(0, weight=1)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(0, weight=0)

    canvas = tk.Canvas(
        outer,
        highlightthickness=0,
        bg=COLOR_SURFACE,
    )
    canvas.grid(row=0, column=0, sticky="nsew")

    inner = tk.Frame(outer, bg=COLOR_CARD)
    inner.grid(row=0, column=0, sticky="nsew")
    inner.columnconfigure(0, weight=1)

    def _on_configure(ev: tk.Event) -> None:
        w, h = ev.width, ev.height
        if w <= 0 or h <= 0:
            return
        canvas.delete("all")
        _rounded_rect(canvas, 0, 0, w, h, CARD_RADIUS, fill=COLOR_CARD, outline=COLOR_CARD)

    canvas.bind("<Configure>", _on_configure)

    lbl = ttk.Label(inner, text=title, style="Card.Title.TLabel")
    lbl.grid(row=0, column=0, sticky="w", pady=(0, 4))
    content = tk.Frame(inner, bg=COLOR_CARD)
    content.grid(row=1, column=0, sticky="ew", pady=(0, 0))
    content.columnconfigure(0, weight=1)
    return content, 0, outer


def _section_card_collapsible(
    parent: tk.Widget,
    title: str,
    row: int,
    on_collapsed: Optional[Callable[[bool], None]] = None,
    on_toggle: Optional[Callable[[], None]] = None,
    initial_expanded: bool = True,
) -> tuple[tk.Frame, tk.Frame]:
    """Create a collapsible card with title and toggle. Returns (content frame, outer frame).
    When collapsed, the entire grey card body is removed from the layout (grid_remove).
    on_collapsed(expanded) is called when toggled so the caller can hide/show e.g. buttons below.
    on_toggle() is called after every toggle so the caller can e.g. resize the window to fit."""
    outer = tk.Frame(parent, bg=COLOR_SURFACE)
    outer.grid(row=row, column=0, sticky="ew", pady=(0, 6))
    parent.columnconfigure(0, weight=1)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(0, weight=0, minsize=0)
    outer.rowconfigure(1, weight=0, minsize=0)

    # Row 0: header bar only (always visible; no grey box)
    header = tk.Frame(outer, bg=COLOR_CARD, cursor="hand2")
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(1, weight=1)
    collapse_lbl = tk.Label(
        header,
        text="\u25bc",
        font=(FONT_FAMILY, 10),
        fg=COLOR_ON_SURFACE_VARIANT,
        bg=COLOR_CARD,
        cursor="hand2",
    )
    collapse_lbl.pack(side="left", padx=(0, 4))
    title_lbl = ttk.Label(header, text=title, style="Card.Title.TLabel")
    title_lbl.pack(side="left", fill="x", expand=True, anchor="w")

    # Row 1: entire grey card body (canvas + content); removed from layout when collapsed
    content_wrapper = tk.Frame(outer, bg=COLOR_SURFACE)
    content_wrapper.grid(row=1, column=0, sticky="ew")
    content_wrapper.columnconfigure(0, weight=1)
    content_wrapper.rowconfigure(0, weight=0)

    canvas = tk.Canvas(
        content_wrapper,
        highlightthickness=0,
        bg=COLOR_SURFACE,
    )
    canvas.grid(row=0, column=0, sticky="nsew")

    content_inner = tk.Frame(content_wrapper, bg=COLOR_CARD)
    content_inner.grid(row=0, column=0, sticky="nsew")
    content_inner.columnconfigure(0, weight=1)

    def _on_configure(ev: tk.Event) -> None:
        w, h = ev.width, ev.height
        if w <= 0 or h <= 0:
            return
        canvas.delete("all")
        _rounded_rect(canvas, 0, 0, w, h, CARD_RADIUS, fill=COLOR_CARD, outline=COLOR_CARD)

    canvas.bind("<Configure>", _on_configure)

    content = tk.Frame(content_inner, bg=COLOR_CARD)
    content.grid(row=0, column=0, sticky="ew", pady=(0, 0))
    content.columnconfigure(0, weight=1)

    expanded: List[bool] = [initial_expanded]

    def _toggle() -> None:
        expanded[0] = not expanded[0]
        if expanded[0]:
            content_wrapper.grid()
            collapse_lbl.config(text="\u25bc")
        else:
            content_wrapper.grid_remove()
            collapse_lbl.config(text="\u25b6")
        if on_collapsed:
            on_collapsed(expanded[0])
        if on_toggle:
            on_toggle()

    def _on_header_click(_e: tk.Event) -> None:
        _toggle()

    if not initial_expanded:
        content_wrapper.grid_remove()
        collapse_lbl.config(text="\u25b6")
        if on_collapsed:
            on_collapsed(False)

    collapse_lbl.bind("<Button-1>", _on_header_click)
    title_lbl.bind("<Button-1>", _on_header_click)
    header.bind("<Button-1>", _on_header_click)
    return content, outer


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
    # Minimum size: width for layout; height low so window shrinks when sections are collapsed
    _min_w, _min_h = 680, 320
    _default_h = 800  # initial height when all sections expanded (no saved geometry)
    win.minsize(_min_w, _min_h)
    saved_geom = app_config.get_settings_window_geometry()
    if saved_geom:
        # Parse "WxH" or "WxH+X+Y" and clamp to minimum so window can shrink when collapsed
        parts = saved_geom.split("+")
        size_part = parts[0]
        pos_part = "+" + "+".join(parts[1:]) if len(parts) > 1 else ""
        if "x" in size_part:
            try:
                ws, hs = size_part.split("x", 1)
                w, h = int(ws.strip()), int(hs.strip())
                w = max(_min_w, w)
                h = max(_min_h, h)
                saved_geom = f"{w}x{h}{pos_part}"
            except (ValueError, TypeError):
                saved_geom = f"{_min_w}x{_default_h}"
        else:
            saved_geom = f"{_min_w}x{_default_h}"
        try:
            win.geometry(saved_geom)
        except tk.TclError:
            win.geometry(f"{_min_w}x{_default_h}")
    else:
        win.geometry(f"{_min_w}x{_default_h}")
    win.configure(bg=COLOR_SURFACE)
    _apply_theme(win)
    log.info("show_settings: theme applied")

    frame = ttk.Frame(win, padding=PAD_WINDOW)
    frame.grid(row=0, column=0, sticky="nsew")
    win.columnconfigure(0, weight=1)
    win.rowconfigure(0, weight=0)  # no expand: window shrinks when sections are collapsed

    # Resize window to fit content (call after any section collapse/expand)
    _win_geom_extra_w = 16
    _win_geom_extra_h = 70  # title bar + borders

    def _fit_window_to_content() -> None:
        def _do_fit() -> None:
            try:
                win.update_idletasks()
                frame.update_idletasks()
                rw = frame.winfo_reqwidth()
                rh = frame.winfo_reqheight()
                w = max(_min_w, rw + _win_geom_extra_w)
                h = max(_min_h, rh + _win_geom_extra_h)
                win.geometry(f"{w}x{h}")
            except tk.TclError:
                pass

        win.after(10, _do_fit)

    row = 0

    # --- Server / base URL (collapsible card) ---
    sec, _ = _section_card_collapsible(
        frame, "Server", row, on_collapsed=None, on_toggle=_fit_window_to_content, initial_expanded=False
    )
    row += 1
    r = 0
    current_url_text = "Current: " + get_base_url()
    url_mode_var = tk.StringVar(value=app_config.get_base_url_mode())
    manual_url_var = tk.StringVar(
        value=app_config.get_manual_base_url() or app_config.DEFAULT_REMOTE_BASE_URL
    )
    current_url_label = ttk.Label(sec, text=current_url_text, style="Card.Caption.TLabel", wraplength=420)
    current_url_label.grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 4))
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
        style="Card.TRadiobutton",
    ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 2))
    r += 1
    ttk.Radiobutton(
        sec,
        text="Manual base URL",
        variable=url_mode_var,
        value="manual",
        command=on_mode_change,
        style="Card.TRadiobutton",
    ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 2))
    r += 1
    manual_entry = ttk.Entry(sec, textvariable=manual_url_var, width=52)
    manual_entry.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, 2))
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

    # --- Sync folder (collapsible card) ---
    sec2, _ = _section_card_collapsible(
        frame, "Sync folder", row, on_collapsed=None, on_toggle=_fit_window_to_content, initial_expanded=False
    )
    row += 1
    r2 = 0
    sync_path = app_config.get_sync_folder_path()
    path_var = tk.StringVar(value=str(sync_path))
    path_label = ttk.Label(sec2, textvariable=path_var, style="Card.Caption.TLabel", wraplength=420)
    path_label.grid(row=r2, column=0, columnspan=2, sticky="w", pady=(0, 4))
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
    choose_btn.grid(row=r2, column=0, columnspan=2, sticky="w", pady=(0, 2))
    sec2.columnconfigure(0, weight=1)
    log.info("show_settings: sync folder section done")

    # --- Startup (collapsible card) ---
    sec3, _ = _section_card_collapsible(
        frame, "Startup", row, on_collapsed=None, on_toggle=_fit_window_to_content, initial_expanded=False
    )
    row += 1
    r3 = 0
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

    # --- Account (card): storage, change password, logout ---
    if api:
        sec4, _ = _section_card_collapsible(
            frame, "Account", row, on_collapsed=None, on_toggle=_fit_window_to_content
        )
        row += 1
        r4 = 0

        # Storage space: circular progress + "Used: X GiB" and "Available: Y GiB"
        storage_sec = tk.Frame(sec4, bg=COLOR_CARD)
        storage_sec.grid(row=r4, column=0, columnspan=2, sticky="w", pady=(0, 4))
        storage_sec.columnconfigure(1, minsize=200)
        r4 += 1
        _storage_circle_size = 64
        _storage_canvas_container = tk.Frame(storage_sec, width=_storage_circle_size, height=_storage_circle_size, bg=COLOR_CARD)
        _storage_canvas_container.grid(row=0, column=0, sticky="nw", padx=(0, 12), pady=(0, 2))
        _storage_canvas_container.grid_propagate(False)
        _storage_canvas = tk.Canvas(
            _storage_canvas_container,
            width=_storage_circle_size,
            height=_storage_circle_size,
            highlightthickness=0,
            bg=COLOR_CARD,
        )
        _storage_canvas.pack(fill="both", expand=True)
        storage_used_var = tk.StringVar(value="…")
        storage_available_var = tk.StringVar(value="…")
        ttk.Label(storage_sec, text="Storage space", style="Card.Title.TLabel").grid(
            row=0, column=1, sticky="w", pady=(0, 2)
        )
        ttk.Label(storage_sec, text="Used:", style="Card.Caption.TLabel").grid(
            row=1, column=1, sticky="w", pady=(0, 0)
        )
        storage_used_label = ttk.Label(
            storage_sec, textvariable=storage_used_var, style="Card.TLabel", wraplength=400
        )
        storage_used_label.grid(row=2, column=1, sticky="w", pady=(0, 0))
        ttk.Label(storage_sec, text="Available:", style="Card.Caption.TLabel").grid(
            row=3, column=1, sticky="w", pady=(4, 0)
        )
        storage_available_label = ttk.Label(
            storage_sec, textvariable=storage_available_var, style="Card.TLabel", wraplength=400
        )
        storage_available_label.grid(row=4, column=1, sticky="w", pady=(0, 2))
        _last_storage_used: List[int] = [0]
        _last_storage_limit: List[Optional[int]] = [None]

        def _draw_storage_circle(used: int, limit: Optional[int]) -> None:
            _last_storage_used[0] = used
            _last_storage_limit[0] = limit
            sz = _storage_circle_size
            _storage_canvas.delete("all")
            _storage_canvas.configure(bg=COLOR_CARD, width=sz, height=sz)
            cx, cy = sz / 2, sz / 2
            r = (sz / 2) - 4
            # Background circle (grey track)
            _storage_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#e0e0e0", outline="#e0e0e0")
            if limit is not None and limit > 0:
                pct = min(1.0, used / limit)
                # Pie slice for used portion (blue): from top (-90°) clockwise
                if pct >= 1.0:
                    _storage_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=COLOR_PRIMARY, outline=COLOR_PRIMARY)
                elif pct > 0:
                    _storage_canvas.create_arc(
                        cx - r, cy - r, cx + r, cy + r,
                        start=-90, extent=-360 * pct, fill=COLOR_PRIMARY, outline=COLOR_PRIMARY, style=tk.PIESLICE,
                    )
            _storage_canvas.update_idletasks()

        _storage_result_queue: "queue.Queue[Optional[dict]]" = queue.Queue()

        def _apply_storage_data(data: Optional[dict]) -> None:
            """Update storage labels and circle on the main thread. data is None on error."""
            try:
                if not storage_used_label.winfo_exists():
                    return
                if data is None:
                    storage_used_var.set("unavailable")
                    storage_available_var.set("—")
                    _draw_storage_circle(0, None)
                    return
                used = int(data.get("used_bytes") or 0)
                limit_raw = data.get("limit_bytes")
                limit = int(limit_raw) if limit_raw is not None else None
                storage_used_var.set(_format_storage_bytes(used))
                if limit is not None:
                    available = max(0, limit - used)
                    storage_available_var.set(_format_storage_bytes(available))
                else:
                    storage_available_var.set("No maximum")
                _draw_storage_circle(used, limit)
                def _redraw_later() -> None:
                    try:
                        if _storage_canvas.winfo_exists():
                            _draw_storage_circle(_last_storage_used[0], _last_storage_limit[0])
                    except tk.TclError:
                        pass
                win.after(200, _redraw_later)
            except (tk.TclError, ValueError) as e:
                log.debug("Storage UI update skipped: %s", e)

        def _poll_storage_queue() -> None:
            """Run on main thread: consume storage result from queue and update UI."""
            try:
                data = _storage_result_queue.get_nowait()
                _apply_storage_data(data)
            except queue.Empty:
                if storage_used_label.winfo_exists():
                    win.after(100, _poll_storage_queue)
            except (tk.TclError, ValueError) as e:
                log.debug("Storage poll skipped: %s", e)

        def _load_storage_async() -> None:
            if not api:
                return

            def _fetch() -> None:
                try:
                    data = api.get_storage()
                except Exception as e:
                    log.warning("Could not load storage: %s", e)
                    data = None
                _storage_result_queue.put(data)

            threading.Thread(target=_fetch, daemon=True).start()
            win.after(100, _poll_storage_queue)

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
        chpwd_btn.grid(row=r4, column=0, sticky="w", pady=(0, 2))
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

            logout_btn = _secondary_btn(sec4, "Log out", do_logout)
            logout_btn.grid(row=r4, column=1, sticky="w", padx=(PAD_ROW, 0), pady=(0, 2))

    # --- Admin: user management (collapsible card); buttons below card; visible only for admins ---
    admin_sec: Optional[tk.Frame] = None
    admin_buttons_row: Optional[int] = None
    admin_card_outer: Optional[tk.Frame] = None
    admin_buttons_ref: List[Optional[tk.Frame]] = [None]

    def _on_admin_collapsed(expanded: bool) -> None:
        if admin_buttons_ref[0] is None:
            return
        if expanded:
            admin_buttons_ref[0].grid(row=admin_buttons_row, column=0, sticky="w", pady=(8, 0))
        else:
            admin_buttons_ref[0].grid_remove()

    if api:
        sec5, admin_card_outer = _section_card_collapsible(
            frame,
            "User management (admin)",
            row,
            on_collapsed=_on_admin_collapsed,
            on_toggle=_fit_window_to_content,
            initial_expanded=False,
        )
        row += 1
        admin_buttons_row = row
        row += 1
        admin_sec = sec5
        admin_placeholder = ttk.Label(sec5, text="Loading…", style="Card.Caption.TLabel")
        admin_placeholder.grid(row=0, column=0, sticky="w", pady=(0, 4))
        sec5.columnconfigure(0, weight=1)

    def _load_admin_section_async() -> None:
        """Run after window is shown: fetch is_admin; hide section if not admin, else show list."""
        if not api or admin_sec is None or admin_card_outer is None:
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
            admin_card_outer.grid_remove()
            _fit_window_to_content()
            return
        r5 = 0
        users_listbox_frame = tk.Frame(admin_sec, bg=COLOR_CARD)
        users_listbox_frame.grid(row=r5, column=0, columnspan=2, sticky="nsew", pady=(0, 2))
        users_listbox_frame.columnconfigure(0, weight=1)
        users_listbox_frame.rowconfigure(0, weight=1)
        r5 += 1
        _avatar_size = 28
        users_canvas = tk.Canvas(
            users_listbox_frame,
            highlightthickness=0,
            bg=COLOR_CARD,
        )
        scroll = ttk.Scrollbar(users_listbox_frame, orient="vertical")
        users_inner = tk.Frame(users_canvas, bg=COLOR_CARD)
        def _on_inner_configure(_e: tk.Event) -> None:
            users_canvas.configure(scrollregion=users_canvas.bbox("all"))

        users_inner.bind("<Configure>", _on_inner_configure)
        win_id = users_canvas.create_window((0, 0), window=users_inner, anchor="nw")
        users_canvas.bind(
            "<Configure>",
            lambda ev: users_canvas.itemconfigure(win_id, width=ev.width),
        )
        users_canvas.configure(yscrollcommand=scroll.set)
        scroll.configure(command=users_canvas.yview)
        users_canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        user_data: List[dict] = []
        selected_user_idx: List[Optional[int]] = [None]

        def _draw_avatar(canvas: tk.Canvas, letter: str) -> None:
            canvas.delete("all")
            r = _avatar_size / 2 - 2
            cx, cy = _avatar_size / 2, _avatar_size / 2
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=COLOR_OUTLINE, outline=COLOR_ON_SURFACE_VARIANT)
            canvas.create_text(cx, cy, text=letter.upper(), fill=COLOR_ON_SURFACE, font=(FONT_FAMILY, 11, "bold"))

        def refresh_users_list() -> None:
            selected_user_idx[0] = None
            for w in users_inner.grid_slaves():
                w.destroy()
            try:
                users = api.list_users()
                user_data.clear()
                for i, u in enumerate(users):
                    email = u.get("email", "")
                    name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
                    display = f"{email} ({name})" if name else email
                    user_data.append(u)
                    row_f = tk.Frame(users_inner, bg=COLOR_CARD, cursor="hand2")
                    lbl = tk.Label(
                        row_f,
                        text=display,
                        font=(FONT_FAMILY, FONT_SIZE),
                        fg=COLOR_ON_SURFACE,
                        bg=COLOR_CARD,
                        anchor="w",
                    )
                    avatar_canvas = tk.Canvas(
                        row_f,
                        width=_avatar_size,
                        height=_avatar_size,
                        highlightthickness=0,
                        bg=COLOR_CARD,
                    )
                    first = (u.get("first_name") or "?")[0] if u.get("first_name") else (email or "?")[0]
                    _draw_avatar(avatar_canvas, first)
                    lbl.pack(side="left", fill="x", expand=True, padx=(0, 8))
                    avatar_canvas.pack(side="right")
                    row_f.grid(row=i, column=0, sticky="ew", pady=1)
                    users_inner.columnconfigure(0, weight=1)
                    idx = i

                    def _on_row_click(
                        _e: tk.Event, index: int = idx, rframe: tk.Frame = row_f
                    ) -> None:
                        selected_user_idx[0] = index
                        for rw in users_inner.grid_slaves():
                            if isinstance(rw, tk.Frame):
                                rw.configure(bg=COLOR_CARD)
                        if rframe.winfo_exists():
                            rframe.configure(bg=COLOR_OUTLINE)

                    row_f.bind("<Button-1>", _on_row_click)
                    lbl.bind("<Button-1>", _on_row_click)
                users_canvas.configure(height=min(140, max(80, len(user_data) * 32)))
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
            idx = selected_user_idx[0]
            if idx is None or idx >= len(user_data):
                messagebox.showinfo("Info", "Select a user to delete.", parent=win)
                return
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

        def set_storage_limit_dialog() -> None:
            idx = selected_user_idx[0]
            if idx is None or idx >= len(user_data):
                messagebox.showinfo("Info", "Select a user to set storage limit.", parent=win)
                return
                return
            u = user_data[idx]
            email = u.get("email", "")
            used = u.get("storage_used_bytes") or 0
            limit = u.get("storage_limit_bytes")
            dlg = tk.Toplevel(win)
            dlg.title("Set storage limit")
            dlg.transient(win)
            dlg.resizable(False, False)
            dlg.minsize(360, 220)
            dlg.geometry("360x220")
            dlg.configure(bg=COLOR_SURFACE)
            _apply_theme(dlg)
            f = ttk.Frame(dlg, padding=PAD_WINDOW)
            f.grid(row=0, column=0, sticky="nsew")
            dlg.columnconfigure(0, weight=1)
            dlg.rowconfigure(0, weight=1)
            r = 0
            ttk.Label(f, text=f"User: {email}", style="Caption.TLabel").grid(
                row=r, column=0, sticky="w", pady=(0, 2)
            )
            r += 1
            limit_str = _format_storage_bytes(limit) if limit is not None else "Server default"
            ttk.Label(f, text=f"Current: {_format_storage_bytes(used)} used, limit {limit_str}", style="Caption.TLabel").grid(
                row=r, column=0, sticky="w", pady=(0, PAD_ROW))
            r += 1
            no_limit_var = tk.BooleanVar(value=limit is None)
            ttk.Checkbutton(
                f, text="No per-user limit (use server default)",
                variable=no_limit_var,
            ).grid(row=r, column=0, sticky="w", pady=(PAD_ROW, 2))
            r += 1
            limit_entry_frame = ttk.Frame(f)
            limit_entry_frame.grid(row=r, column=0, sticky="w", pady=(0, PAD_ROW))
            limit_num_var = tk.StringVar(value=str(int(limit / (1024**3))) if limit is not None else "10")
            limit_entry = ttk.Entry(limit_entry_frame, textvariable=limit_num_var, width=10)
            limit_entry.pack(side="left", padx=(0, 4))
            unit_var = tk.StringVar(value="GiB")
            unit_combo = ttk.Combobox(limit_entry_frame, textvariable=unit_var, width=6, state="readonly")
            unit_combo["values"] = ("GiB", "TiB")
            unit_combo.pack(side="left")
            r += 1

            def do_set_limit() -> None:
                if no_limit_var.get():
                    try:
                        api.update_user_storage_limit(email, None)
                        messagebox.showinfo("Done", "Storage limit cleared (server default).", parent=dlg)
                        dlg.destroy()
                        refresh_users_list()
                    except Exception as e:
                        messagebox.showerror("Error", str(e), parent=dlg)
                    return
                try:
                    num = float(limit_num_var.get().strip())
                except ValueError:
                    messagebox.showerror("Error", "Enter a valid number.", parent=dlg)
                    return
                if num <= 0:
                    messagebox.showerror("Error", "Limit must be positive.", parent=dlg)
                    return
                unit = unit_var.get()
                mult = 1024**4 if unit == "TiB" else 1024**3
                limit_bytes = int(num * mult)
                try:
                    api.update_user_storage_limit(email, limit_bytes)
                    messagebox.showinfo("Done", f"Storage limit set to {_format_storage_bytes(limit_bytes)}.", parent=dlg)
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
            _primary_btn(btn_f, "Set limit", do_set_limit, side="left", padx=(0, PAD_ROW))
            _secondary_btn(btn_f, "Cancel", dlg.destroy, side="left")
            f.columnconfigure(0, weight=1)
            dlg.update_idletasks()
            _center(dlg)
            try:
                dlg.grab_set()
            except tk.TclError:
                pass

        btn_frame = ttk.Frame(frame)
        admin_buttons_ref[0] = btn_frame
        btn_frame.grid(row=admin_buttons_row, column=0, sticky="w", pady=(8, 0))
        _secondary_btn(btn_frame, "Refresh list", refresh_users_list, side="left", padx=(0, PAD_ROW))
        _primary_btn(btn_frame, "Create user…", create_user_dialog, side="left", padx=(0, PAD_ROW))
        _secondary_btn(btn_frame, "Delete selected", delete_selected_user, side="left", padx=(0, PAD_ROW))
        _secondary_btn(btn_frame, "Set storage limit…", set_storage_limit_dialog, side="left")
        frame.columnconfigure(0, weight=1)
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
        if api:
            win.after(0, _load_storage_async)
    else:
        log.info("show_settings: entering mainloop")
    if parent is None and api and admin_sec is not None:
        win.after(0, _load_admin_section_async)
    if parent is None and api:
        win.after(0, _load_storage_async)
    if parent is None:
        win.mainloop()
