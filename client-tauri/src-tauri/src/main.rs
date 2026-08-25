// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // Suppress "Failed to load module appmenu-gtk-module" on Linux
    #[cfg(target_os = "linux")]
    std::env::set_var("GTK_MODULES", "");
    brandybox_lib::run()
}
