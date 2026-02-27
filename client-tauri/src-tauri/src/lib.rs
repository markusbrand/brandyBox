//! Brandy Box Tauri app: config, auth, API, sync, tray.

mod api;
mod config;
mod credentials;
mod network;
mod sync;

use api::ApiClient;
use serde::Serialize;
use tauri::{Emitter, Manager};
use std::path::PathBuf;
use std::sync::Mutex;

#[derive(Default)]
#[allow(dead_code)]
struct AppState {
    /// Cached access token (set after login or refresh). Cleared on logout.
    access_token: Mutex<Option<String>>,
}

#[derive(Serialize)]
pub struct SyncProgressPayload {
    pub phase: String,
    pub current: u64,
    pub total: u64,
}

#[tauri::command]
fn get_base_url() -> String {
    network::get_base_url()
}

#[tauri::command]
fn get_sync_folder_path() -> String {
    config::get_sync_folder_path().to_string_lossy().to_string()
}

#[tauri::command]
fn set_sync_folder_path(folder: String) {
    config::set_sync_folder_path(PathBuf::from(folder));
}

#[tauri::command]
fn user_has_set_sync_folder() -> bool {
    config::user_has_set_sync_folder()
}

#[tauri::command]
fn get_default_sync_folder() -> String {
    config::get_default_sync_folder().to_string_lossy().to_string()
}

#[tauri::command]
fn get_autostart() -> bool {
    config::get_autostart()
}

#[tauri::command]
fn set_autostart(enabled: bool) {
    config::set_autostart(enabled);
}

#[tauri::command]
fn get_base_url_mode() -> String {
    config::get_base_url_mode()
}

#[tauri::command]
fn set_base_url_mode(mode: String) {
    config::set_base_url_mode(mode);
}

#[tauri::command]
fn get_manual_base_url() -> String {
    config::get_manual_base_url()
}

#[tauri::command]
fn set_manual_base_url(url: String) {
    config::set_manual_base_url(url);
}

#[tauri::command]
fn login(email: String, password: String) -> Result<serde_json::Value, String> {
    let base_url = network::get_base_url();
    let client = ApiClient::new(base_url);
    let res = client.login(email.trim(), password.trim()).map_err(|e| {
        if e.contains("401") {
            "Invalid email or password.".to_string()
        } else {
            e
        }
    })?;
    credentials::set_stored(email.trim(), &res.refresh_token);
    Ok(serde_json::json!({
        "access_token": res.access_token,
        "refresh_token": res.refresh_token
    }))
}

#[tauri::command]
fn logout() {
    credentials::clear_stored();
}

#[tauri::command]
fn get_stored_email() -> Option<String> {
    credentials::get_stored().map(|(email, _)| email)
}

#[tauri::command]
fn get_valid_access_token() -> Option<String> {
    let (email, refresh_token) = credentials::get_stored()?;
    let base_url = network::get_base_url();
    let client = ApiClient::new(base_url);
    let res = client.refresh(&refresh_token).ok()?;
    credentials::set_stored(&email, &res.refresh_token);
    Some(res.access_token)
}

#[tauri::command]
fn api_me() -> Result<serde_json::Value, String> {
    let token = get_valid_access_token().ok_or("Not logged in")?;
    let base_url = network::get_base_url();
    let mut client = ApiClient::new(base_url);
    client.set_access_token(Some(token));
    let user = client.me()?;
    Ok(serde_json::json!({
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_admin": user.is_admin
    }))
}

#[tauri::command]
fn api_get_storage() -> Result<serde_json::Value, String> {
    let token = get_valid_access_token().ok_or("Not logged in")?;
    let base_url = network::get_base_url();
    let mut client = ApiClient::new(base_url);
    client.set_access_token(Some(token));
    let s = client.get_storage()?;
    Ok(serde_json::json!({
        "used_bytes": s.used_bytes,
        "limit_bytes": s.limit_bytes
    }))
}

#[tauri::command]
fn api_change_password(current_password: String, new_password: String) -> Result<(), String> {
    let token = get_valid_access_token().ok_or("Not logged in")?;
    let base_url = network::get_base_url();
    let mut client = ApiClient::new(base_url);
    client.set_access_token(Some(token));
    client.change_password(&current_password, &new_password)
}

#[tauri::command]
fn api_list_users() -> Result<Vec<serde_json::Value>, String> {
    let token = get_valid_access_token().ok_or("Not logged in")?;
    let base_url = network::get_base_url();
    let mut client = ApiClient::new(base_url);
    client.set_access_token(Some(token));
    let users = client.list_users()?;
    Ok(users
        .into_iter()
        .map(|u| {
            serde_json::json!({
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "is_admin": u.is_admin,
                "storage_limit_bytes": u.storage_limit_bytes
            })
        })
        .collect())
}

#[tauri::command]
fn api_create_user(email: String, first_name: String, last_name: String) -> Result<serde_json::Value, String> {
    let token = get_valid_access_token().ok_or("Not logged in")?;
    let base_url = network::get_base_url();
    let mut client = ApiClient::new(base_url);
    client.set_access_token(Some(token));
    client.create_user(&email, &first_name, &last_name)
}

#[tauri::command]
fn api_update_user_storage_limit(email: String, limit_bytes: Option<i64>) -> Result<serde_json::Value, String> {
    let token = get_valid_access_token().ok_or("Not logged in")?;
    let base_url = network::get_base_url();
    let mut client = ApiClient::new(base_url);
    client.set_access_token(Some(token));
    client.update_user_storage_limit(&email, limit_bytes)
}

#[tauri::command]
fn api_delete_user(email: String) -> Result<(), String> {
    let token = get_valid_access_token().ok_or("Not logged in")?;
    let base_url = network::get_base_url();
    let mut client = ApiClient::new(base_url);
    client.set_access_token(Some(token));
    client.delete_user(&email)
}

#[tauri::command]
fn open_sync_folder() -> Result<(), String> {
    let path = config::get_sync_folder_path();
    if !path.exists() {
        let _ = std::fs::create_dir_all(&path);
    }
    open::that(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn run_sync(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    if !config::user_has_set_sync_folder() {
        return Err("Sync folder not set".to_string());
    }
    let token = get_valid_access_token().ok_or("Not logged in")?;
    let base_url = network::get_base_url();
    let root = config::get_sync_folder_path();
    if !root.exists() {
        let _ = std::fs::create_dir_all(&root);
    }
    sync::set_sync_status(sync::SyncStatus::Syncing);
    let _ = app.emit("sync-status", sync::get_sync_status_payload());
    std::thread::spawn(move || {
        let mut client = ApiClient::new(base_url);
        client.set_access_token(Some(token));
        let result = sync::run_sync(&mut client, &root);
        match &result {
            Ok((bytes_downloaded, bytes_uploaded, warning)) => {
                if let Some(msg) = warning {
                    sync::set_sync_status(sync::SyncStatus::Warning(msg.clone()));
                } else {
                    sync::set_sync_status(sync::SyncStatus::Synced);
                }
                let _ = app.emit(
                    "sync-completed",
                    serde_json::json!({ "bytesDownloaded": bytes_downloaded, "bytesUploaded": bytes_uploaded }),
                );
            }
            Err(e) => {
                eprintln!("Brandy Box sync error: {}", e);
                sync::set_sync_status(sync::SyncStatus::Error(e.clone()));
            }
        }
        let _ = app.emit("sync-status", sync::get_sync_status_payload());
    });
    Ok(serde_json::json!({ "started": true }))
}

#[tauri::command]
fn quit_app() {
    std::process::exit(0);
}

const DEFAULT_SETTINGS_WIDTH: u32 = 520;
const DEFAULT_SETTINGS_HEIGHT: u32 = 640;
const TRAY_SIDE_MARGIN: i32 = 16;

/// Restore or set main (settings) window position and size, then show it.
#[tauri::command]
fn show_main_window(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        if let Some(geom) = config::get_settings_window_geometry() {
            if let Some((x, y, w, h)) = parse_geometry(&geom) {
                let pos = tauri::PhysicalPosition::new(x, y);
                let size = tauri::PhysicalSize::new(w, h);
                if win.set_position(pos).is_ok() && win.set_size(size).is_ok() {
                    log::debug!("Restored settings window geometry: {}", geom);
                }
            }
        } else {
            if let Ok(Some(monitor)) = win.primary_monitor() {
                let work = monitor.work_area();
                let wa_x = work.position.x;
                let wa_y = work.position.y;
                let wa_w = work.size.width as i32;
                let wa_h = work.size.height as i32;
                let win_w = DEFAULT_SETTINGS_WIDTH as i32;
                let win_h = DEFAULT_SETTINGS_HEIGHT as i32;
                let x = (wa_x + wa_w - win_w - TRAY_SIDE_MARGIN).max(wa_x);
                let y = (wa_y + TRAY_SIDE_MARGIN).min(wa_y + wa_h - win_h);
                let _ = win.set_position(tauri::PhysicalPosition::new(x, y));
                let _ = win.set_size(tauri::PhysicalSize::new(
                    DEFAULT_SETTINGS_WIDTH,
                    DEFAULT_SETTINGS_HEIGHT,
                ));
                log::debug!(
                    "Positioned settings window near tray: ({}, {})",
                    x,
                    y
                );
            }
        }
        let _ = win.show();
        let _ = win.unminimize();
        let _ = win.set_focus();
    }
}

#[tauri::command]
fn hide_main_window(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.hide();
    }
}

fn parse_geometry(s: &str) -> Option<(i32, i32, u32, u32)> {
    let parts: Vec<&str> = s.split(',').map(str::trim).collect();
    if parts.len() != 4 {
        return None;
    }
    let x: i32 = parts[0].parse().ok()?;
    let y: i32 = parts[1].parse().ok()?;
    let w: u32 = parts[2].parse().ok()?;
    let h: u32 = parts[3].parse().ok()?;
    if w == 0 || h == 0 {
        return None;
    }
    Some((x, y, w, h))
}

#[tauri::command]
fn get_sync_progress() -> Option<SyncProgressPayload> {
    sync::get_sync_progress().map(|p| SyncProgressPayload {
        phase: p.phase,
        current: p.current,
        total: p.total,
    })
}

#[tauri::command]
fn get_sync_status() -> serde_json::Value {
    sync::get_sync_status_payload()
}

fn try_acquire_single_instance_lock() -> bool {
    use fs2::FileExt;
    if std::env::var("BRANDYBOX_CONFIG_DIR").map(|s| !s.trim().is_empty()).unwrap_or(false) {
        return true;
    }
    let path = config::get_instance_lock_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let f = match std::fs::OpenOptions::new().write(true).create(true).truncate(true).open(&path) {
        Ok(f) => f,
        Err(_) => return false,
    };
    if f.try_lock_exclusive().is_err() {
        return false;
    }
    std::mem::forget(f);
    true
}

const BACKGROUND_SYNC_INTERVAL_SECS: u64 = 60;
const BACKGROUND_SYNC_INITIAL_DELAY_SECS: u64 = 15;

fn spawn_background_sync_loop(app: tauri::AppHandle) {
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_secs(BACKGROUND_SYNC_INITIAL_DELAY_SECS));
        loop {
            let (status, _) = sync::get_sync_status();
            if status != "syncing"
                && config::user_has_set_sync_folder()
                && get_valid_access_token().is_some()
            {
                let root = config::get_sync_folder_path();
                if root.exists() || std::fs::create_dir_all(&root).is_ok() {
                    if let Some(token) = get_valid_access_token() {
                        let base_url = network::get_base_url();
                        sync::set_sync_status(sync::SyncStatus::Syncing);
                        let _ = app.emit("sync-status", sync::get_sync_status_payload());
                        let mut client = ApiClient::new(base_url);
                        client.set_access_token(Some(token));
                        let result = sync::run_sync(&mut client, &root);
                        match &result {
                            Ok((bytes_downloaded, bytes_uploaded, warning)) => {
                                if let Some(msg) = warning {
                                    sync::set_sync_status(sync::SyncStatus::Warning(msg.clone()));
                                } else {
                                    sync::set_sync_status(sync::SyncStatus::Synced);
                                }
                                let _ = app.emit(
                                    "sync-completed",
                                    serde_json::json!({ "bytesDownloaded": bytes_downloaded, "bytesUploaded": bytes_uploaded }),
                                );
                            }
                            Err(e) => {
                                eprintln!("Brandy Box sync error: {}", e);
                                sync::set_sync_status(sync::SyncStatus::Error(e.clone()));
                            }
                        }
                        let _ = app.emit("sync-status", sync::get_sync_status_payload());
                    }
                }
            }
            std::thread::sleep(std::time::Duration::from_secs(BACKGROUND_SYNC_INTERVAL_SECS));
        }
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    if !try_acquire_single_instance_lock() {
        eprintln!("Another instance is already running.");
        std::process::exit(1);
    }
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            spawn_background_sync_loop(app.handle().clone());
            if let Some(win) = app.get_webview_window("main") {
                if let Some(geom) = config::get_settings_window_geometry() {
                    if let Some((x, y, w, h)) = parse_geometry(&geom) {
                        let _ = win.set_position(tauri::PhysicalPosition::new(x, y));
                        let _ = win.set_size(tauri::PhysicalSize::new(w, h));
                    }
                } else if let Ok(Some(monitor)) = win.primary_monitor() {
                    let work = monitor.work_area();
                    let wa_x = work.position.x;
                    let wa_y = work.position.y;
                    let wa_w = work.size.width as i32;
                    let wa_h = work.size.height as i32;
                    let win_w = DEFAULT_SETTINGS_WIDTH as i32;
                    let win_h = DEFAULT_SETTINGS_HEIGHT as i32;
                    let x = (wa_x + wa_w - win_w - TRAY_SIDE_MARGIN).max(wa_x);
                    let y = (wa_y + TRAY_SIDE_MARGIN).min(wa_y + wa_h - win_h);
                    let _ = win.set_position(tauri::PhysicalPosition::new(x, y));
                    let _ = win.set_size(tauri::PhysicalSize::new(
                        DEFAULT_SETTINGS_WIDTH,
                        DEFAULT_SETTINGS_HEIGHT,
                    ));
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {
                    if let (Ok(pos), Ok(sz)) = (window.inner_position(), window.inner_size()) {
                        let geom = format!(
                            "{},{},{},{}",
                            pos.x,
                            pos.y,
                            sz.width,
                            sz.height
                        );
                        log::debug!("Saved settings window geometry: {}", geom);
                        config::set_settings_window_geometry(geom);
                    }
                    let _ = window.hide();
                    api.prevent_close();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_base_url,
            get_sync_folder_path,
            set_sync_folder_path,
            user_has_set_sync_folder,
            get_default_sync_folder,
            get_autostart,
            set_autostart,
            get_base_url_mode,
            set_base_url_mode,
            get_manual_base_url,
            set_manual_base_url,
            login,
            logout,
            get_stored_email,
            get_valid_access_token,
            api_me,
            api_get_storage,
            api_change_password,
            api_list_users,
            api_create_user,
            api_update_user_storage_limit,
            api_delete_user,
            open_sync_folder,
            run_sync,
            get_sync_progress,
            get_sync_status,
            quit_app,
            show_main_window,
            hide_main_window,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
