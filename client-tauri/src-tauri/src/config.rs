//! Client configuration: config dir, sync folder, base URL, autostart.
//! Matches Python client paths and config.json layout.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

const DEFAULT_REMOTE_BASE_URL: &str = "https://brandybox.brandstaetter.rocks";
const CONFIG_FILENAME: &str = "config.json";
const SYNC_STATE_FILENAME: &str = "sync_state.json";
const INSTANCE_LOCK_FILENAME: &str = "instance.lock";

fn expand_tilde(path: &str) -> PathBuf {
    let s = path.trim();
    if s.starts_with('~') {
        let rest = s.trim_start_matches('~').trim_start_matches('/');
        if let Some(home) = dirs::home_dir() {
            return home.join(rest);
        }
    }
    PathBuf::from(s)
}

fn config_dir() -> PathBuf {
    if let Ok(override_dir) = std::env::var("BRANDYBOX_CONFIG_DIR") {
        let s = override_dir.trim();
        if !s.is_empty() {
            return expand_tilde(s);
        }
    }
    #[cfg(windows)]
    {
        let appdata = std::env::var("APPDATA").unwrap_or_else(|_| std::env::var("USERPROFILE").unwrap_or_default());
        PathBuf::from(appdata).join("BrandyBox")
    }
    #[cfg(not(windows))]
    {
        if let Some(xdg) = std::env::var_os("XDG_CONFIG_HOME") {
            PathBuf::from(xdg).join("brandybox")
        } else {
            dirs::home_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join(".config")
                .join("brandybox")
        }
    }
}

#[derive(Default, Clone, Serialize, Deserialize)]
struct ConfigFile {
    sync_folder: Option<String>,
    autostart: Option<bool>,
    base_url_mode: Option<String>,
    manual_base_url: Option<String>,
    settings_window_geometry: Option<String>,
}

fn ensure_config_dir() -> PathBuf {
    let d = config_dir();
    let _ = std::fs::create_dir_all(&d);
    d
}

fn read_config() -> ConfigFile {
    let path = config_dir().join(CONFIG_FILENAME);
    if !path.exists() {
        return ConfigFile::default();
    }
    match std::fs::read_to_string(&path) {
        Ok(s) => serde_json::from_str(&s).unwrap_or_default(),
        Err(_) => ConfigFile::default(),
    }
}

fn write_config(update: impl FnOnce(&mut ConfigFile)) {
    let mut cfg = read_config();
    update(&mut cfg);
    let path = ensure_config_dir().join(CONFIG_FILENAME);
    let _ = std::fs::write(
        path,
        serde_json::to_string_pretty(&cfg).unwrap_or_else(|_| "{}".to_string()),
    );
}

#[allow(dead_code)]
pub fn get_config_path() -> PathBuf {
    ensure_config_dir();
    config_dir().join(CONFIG_FILENAME)
}

pub fn get_instance_lock_path() -> PathBuf {
    config_dir().join(INSTANCE_LOCK_FILENAME)
}

pub fn get_sync_state_path() -> PathBuf {
    ensure_config_dir();
    config_dir().join(SYNC_STATE_FILENAME)
}

pub fn get_default_sync_folder() -> PathBuf {
    dirs::home_dir().unwrap_or_else(|| PathBuf::from(".")).join("brandyBox")
}

pub fn user_has_set_sync_folder() -> bool {
    read_config().sync_folder.map(|s| !s.is_empty()).unwrap_or(false)
}

pub fn get_sync_folder_path() -> PathBuf {
    let raw = read_config().sync_folder.filter(|s| !s.is_empty());
    match raw {
        Some(s) => expand_tilde(&s),
        None => get_default_sync_folder(),
    }
}

pub fn set_sync_folder_path(folder: PathBuf) {
    let s = folder.to_string_lossy().to_string();
    write_config(|c| c.sync_folder = Some(s));
}

pub fn get_autostart() -> bool {
    read_config().autostart.unwrap_or(false)
}

pub fn set_autostart(enabled: bool) {
    write_config(|c| c.autostart = Some(enabled));
    apply_autostart_platform(enabled);
}

pub fn get_base_url_mode() -> String {
    read_config()
        .base_url_mode
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "automatic".to_string())
}

pub fn set_base_url_mode(mode: String) {
    write_config(|c| c.base_url_mode = Some(mode));
}

pub fn get_manual_base_url() -> String {
    read_config()
        .manual_base_url
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|| DEFAULT_REMOTE_BASE_URL.to_string())
}

pub fn set_manual_base_url(url: String) {
    write_config(|c| c.manual_base_url = Some(url.trim().to_string()));
}

/// Gets saved settings window geometry as "x,y,width,height" (physical pixels), or None.
#[allow(dead_code)]
pub fn get_settings_window_geometry() -> Option<String> {
    read_config()
        .settings_window_geometry
        .filter(|s| !s.trim().is_empty())
}

/// Saves settings window geometry string "x,y,width,height" (physical pixels).
#[allow(dead_code)]
pub fn set_settings_window_geometry(geometry: String) {
    let s = geometry.trim().to_string();
    write_config(|c| c.settings_window_geometry = if s.is_empty() { None } else { Some(s) });
}

fn executable_command() -> Vec<String> {
    if cfg!(windows) {
        vec![std::env::current_exe().unwrap_or_else(|_| PathBuf::from("BrandyBox.exe")).to_string_lossy().to_string()]
    } else {
        vec!["BrandyBox".to_string()]
    }
}

fn apply_autostart_platform(enabled: bool) {
    let cmd = executable_command();
    #[cfg(windows)]
    apply_autostart_windows(enabled, &cmd);
    #[cfg(target_os = "macos")]
    apply_autostart_macos(enabled, &cmd);
    #[cfg(all(unix, not(target_os = "macos")))]
    apply_autostart_linux(enabled, &cmd);
}

#[cfg(windows)]
fn apply_autostart_windows(enabled: bool, cmd: &[String]) {
    let startup = std::env::var("APPDATA").map(|a| PathBuf::from(a).join("Microsoft/Windows/Start Menu/Programs/Startup")).unwrap_or_default();
    if !startup.exists() {
        return;
    }
    let lnk = startup.join("BrandyBox.lnk");
    if enabled {
        // Create shortcut via PowerShell (simplified; production may use a crate)
        let target = cmd.first().cloned().unwrap_or_default();
        let args = cmd.get(1..).unwrap_or(&[]).join(" ");
        let ps = format!(
            r#"$s = (New-Object -COM WScript.Shell).CreateShortcut("{}"); $s.TargetPath = "{}"; $s.Arguments = "{}"; $s.Save()"#,
            lnk.display(),
            target.replace('"', "`\""),
            args.replace('"', "`\"")
        );
        let _ = std::process::Command::new("powershell")
            .args(["-NoProfile", "-Command", &ps])
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .output();
    } else if lnk.exists() {
        let _ = std::fs::remove_file(lnk);
    }
}

#[cfg(target_os = "macos")]
fn apply_autostart_macos(enabled: bool, cmd: &[String]) {
    let launch_agents = dirs::home_dir().unwrap_or_else(|| PathBuf::from(".")).join("Library/LaunchAgents");
    let _ = std::fs::create_dir_all(&launch_agents);
    let plist = launch_agents.join("rocks.brandstaetter.brandybox.plist");
    if enabled {
        let args_xml: String = cmd.iter().map(|a| format!("    <string>{}</string>", a)).collect::<Vec<_>>().join("\n");
        let content = format!(
            r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>rocks.brandstaetter.brandybox</string>
  <key>ProgramArguments</key>
  <array>
{}
  </array>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
"#,
            args_xml
        );
        let _ = std::fs::write(plist, content);
    } else if plist.exists() {
        let _ = std::fs::remove_file(plist);
    }
}

#[cfg(all(unix, not(target_os = "macos")))]
fn apply_autostart_linux(enabled: bool, cmd: &[String]) {
    let autostart = dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("autostart");
    let _ = std::fs::create_dir_all(&autostart);
    let desktop = autostart.join("brandybox.desktop");
    if enabled {
        let exec = cmd.join(" ");
        let content = format!(
            "[Desktop Entry]\nType=Application\nName=Brandy Box\nExec={}\nX-GNOME-Autostart-enabled=true\n",
            exec
        );
        let _ = std::fs::write(desktop, content);
    } else if desktop.exists() {
        let _ = std::fs::remove_file(desktop);
    }
}

#[allow(dead_code)]
pub fn clear_sync_state() {
    let content = r#"{"paths": [], "downloaded_paths": [], "file_hashes": {}}"#;
    let _ = std::fs::write(get_sync_state_path(), content);
}
