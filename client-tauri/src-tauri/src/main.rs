// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    #[cfg(target_os = "linux")]
    {
        // Suppress "Failed to load module appmenu-gtk-module" on Linux
        std::env::set_var("GTK_MODULES", "");
        // Use x11 backend for GTK on Linux so window positioning (set_position/outer_position)
        // and tray integration work properly under Wayland/XWayland compositors (e.g. KDE Plasma / GNOME).
        if std::env::var("GDK_BACKEND").is_err() && std::env::var("DISPLAY").is_ok() {
            std::env::set_var("GDK_BACKEND", "x11");
        }
    }
    brandybox_lib::run()
}
