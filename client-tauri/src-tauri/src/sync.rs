//! Sync engine: list local/remote, diff, propagate deletes, download, upload.
//! Matches Python client logic and sync_state.json layout.

use crate::api::ApiClient;
use crate::config;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::Path;

const SYNC_IGNORE: &[&str] = &[".directory", "Thumbs.db", "Desktop.ini", ".DS_Store"];
#[allow(dead_code)]
const SYNC_MAX_WORKERS: usize = 8;

#[derive(Default, Clone, Serialize, Deserialize)]
struct SyncStateFile {
    paths: Vec<String>,
    downloaded_paths: Vec<String>,
    file_hashes: HashMap<String, String>,
}

fn is_ignored(path_str: &str) -> bool {
    let normalized = path_str.replace('\\', "/");
    if normalized.contains("/.git/") || normalized.starts_with(".git/") {
        return true;
    }
    let name = Path::new(&normalized).file_name().and_then(|n| n.to_str()).unwrap_or("");
    SYNC_IGNORE.contains(&name)
}

fn list_local(root: &Path) -> Vec<(String, f64)> {
    let mut out = Vec::new();
    for e in walkdir::WalkDir::new(root).into_iter().filter_map(|e| e.ok()) {
        if !e.file_type().is_file() {
            continue;
        }
        let rel = match e.path().strip_prefix(root) {
            Ok(r) => r,
            Err(_) => continue,
        };
        let path_str = rel.to_string_lossy().replace('\\', "/");
        if is_ignored(&path_str) {
            continue;
        }
        if let Ok(meta) = e.metadata() {
            if let Ok(mtime) = meta.modified() {
                let t = mtime.duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs_f64();
                out.push((path_str, t));
            }
        }
    }
    out
}

fn load_sync_state() -> SyncStateFile {
    let path = config::get_sync_state_path();
    if !path.exists() {
        return SyncStateFile::default();
    }
    if let Ok(s) = std::fs::read_to_string(&path) {
        if let Ok(f) = serde_json::from_str(&s) {
            return f;
        }
    }
    SyncStateFile::default()
}

fn save_sync_state(state: &SyncStateFile) {
    let path = config::get_sync_state_path();
    let _ = std::fs::create_dir_all(path.parent().unwrap_or(Path::new(".")));
    let _ = std::fs::write(path, serde_json::to_string_pretty(state).unwrap_or_default());
}

#[derive(Clone)]
pub struct SyncProgress {
    pub phase: String,
    pub current: u64,
    pub total: u64,
}

static SYNC_PROGRESS: std::sync::Mutex<Option<SyncProgress>> = std::sync::Mutex::new(None);

#[derive(Clone)]
pub enum SyncStatus {
    Idle,
    Syncing,
    Synced,
    Error(String),
}

static SYNC_STATUS: std::sync::Mutex<SyncStatus> = std::sync::Mutex::new(SyncStatus::Idle);

pub fn get_sync_status() -> (String, Option<String>) {
    let guard = match SYNC_STATUS.lock() {
        Ok(g) => g,
        Err(_) => return ("idle".to_string(), None),
    };
    match &*guard {
        SyncStatus::Idle => ("idle".to_string(), None),
        SyncStatus::Syncing => ("syncing".to_string(), None),
        SyncStatus::Synced => ("synced".to_string(), None),
        SyncStatus::Error(msg) => ("error".to_string(), Some(msg.clone())),
    }
}

/// Payload for the sync-status Tauri event (status + optional error message).
pub fn get_sync_status_payload() -> serde_json::Value {
    let (status, message) = get_sync_status();
    serde_json::json!({ "status": status, "message": message })
}

pub fn set_sync_status(status: SyncStatus) {
    let _ = SYNC_STATUS.lock().map(|mut g| *g = status);
}

pub fn get_sync_progress() -> Option<SyncProgress> {
    SYNC_PROGRESS.lock().ok().and_then(|g| g.clone())
}

fn set_progress(phase: &str, current: u64, total: u64) {
    let _ = SYNC_PROGRESS.lock().map(|mut g| *g = Some(SyncProgress { phase: phase.to_string(), current, total }));
}

pub fn run_sync(client: &mut ApiClient, local_root: &Path) -> Result<(u64, u64), String> {
    let mut state = load_sync_state();
    let last_synced: HashSet<String> = state.paths.iter().cloned().collect();
    let prev_downloaded: HashSet<String> = state.downloaded_paths.iter().cloned().collect();

    set_progress("listing", 0, 0);
    let local_list = list_local(local_root);
    let remote_list = client.list_files()?;

    let local_by_path: HashMap<String, f64> = local_list.iter().cloned().collect();
    let remote_by_path: HashMap<String, f64> = remote_list.iter().map(|i| (i.path.clone(), i.mtime)).collect();
    let remote_hashes: HashMap<String, String> = remote_list.iter().filter_map(|i| i.hash.clone().map(|h| (i.path.clone(), h))).collect();

    let current_local: HashSet<String> = local_by_path.keys().cloned().collect();
    let current_remote: HashSet<String> = remote_by_path.keys().cloned().collect();

    let to_delete_remote: HashSet<String> = last_synced.difference(&current_local).filter(|p| !is_ignored(p)).cloned().collect();
    let to_delete_local: HashSet<String> = last_synced.difference(&current_remote).cloned().collect();

    let mut to_del_remote: Vec<String> = to_delete_remote.into_iter().collect();
    to_del_remote.sort_by(|a, b| b.matches('/').count().cmp(&a.matches('/').count()));

    let mut to_del_local: Vec<String> = to_delete_local.into_iter().collect();
    to_del_local.sort_by(|a, b| b.matches('/').count().cmp(&a.matches('/').count()));

    let total_work = to_del_remote.len() + to_del_local.len()
        + current_remote.difference(&current_local).filter(|p| !is_ignored(p)).count()
        + current_local.difference(&current_remote).filter(|p| !is_ignored(p)).count();
    let total_work = total_work as u64;
    let mut done = 0u64;

    for path in &to_del_remote {
        set_progress("delete_server", done, total_work);
        client.delete_file(&path).map_err(|e| format!("Delete server {}: {}", path, e))?;
        done += 1;
    }
    for path in &to_del_local {
        set_progress("delete_local", done, total_work);
        let full = local_root.join(path.replace('/', std::path::MAIN_SEPARATOR_STR));
        if full.exists() && full.is_file() {
            let _ = std::fs::remove_file(&full);
            let mut parent = full.parent();
            while let Some(p) = parent {
                if p != local_root && p.read_dir().map(|mut d| d.next().is_none()).unwrap_or(false) {
                    let _ = std::fs::remove_dir(p);
                    parent = p.parent();
                } else {
                    break;
                }
            }
        }
        done += 1;
    }

    let to_del_local_set: HashSet<String> = to_del_local.iter().cloned().collect();
    let to_del_remote_set: HashSet<String> = to_del_remote.iter().cloned().collect();
    let remaining_local: HashSet<String> = current_local.difference(&to_del_local_set).cloned().collect();
    let remaining_remote: HashSet<String> = current_remote.difference(&to_del_remote_set).cloned().collect();
    let base_synced: HashSet<String> = remaining_local.intersection(&remaining_remote).filter(|p| !is_ignored(p)).cloned().collect();
    state.paths = base_synced.iter().cloned().collect();
    state.paths.sort();
    // Do not save_sync_state here: state.paths would omit files we are about to upload,
    // so the next sync could re-download them after user deletes locally. Only persist at the end.

    let mut to_download: Vec<String> = current_remote
        .difference(&current_local)
        .filter(|p| !is_ignored(p))
        .cloned()
        .collect();
    to_download.retain(|path| !to_del_remote_set.contains(path));
    for (path, local_mtime) in &local_list {
        if !is_ignored(path) && current_remote.contains(path) {
            let remote_mtime = remote_by_path.get(path).copied().unwrap_or(0.0);
            if remote_mtime > *local_mtime {
                to_download.push(path.clone());
            }
        }
    }
    to_download.sort();
    to_download.dedup();
    let to_upload: Vec<String> = local_list
        .iter()
        .filter(|(path, _)| !is_ignored(path))
        .filter(|(path, local_mtime)| {
            !current_remote.contains(path) || *local_mtime > remote_by_path.get(path).copied().unwrap_or(0.0)
        })
        .map(|(path, _)| path.clone())
        .collect();

    let mut bytes_downloaded = 0u64;
    for path in &to_download {
        set_progress("download", done, total_work);
        let skip = prev_downloaded.contains(path);
        let local_path = local_root.join(path.replace('/', std::path::MAIN_SEPARATOR_STR));
        if skip && local_path.exists() && local_path.is_file() {
            done += 1;
            continue;
        }
        if let Some(ref hash) = remote_hashes.get(path) {
            if state.file_hashes.get(path.as_str()) == Some(hash) && local_path.exists() && local_path.is_file() {
                done += 1;
                continue;
            }
        }
        match client.download_file(path) {
            Ok(body) => {
                bytes_downloaded += body.len() as u64;
                if let Some(parent) = local_path.parent() {
                    let _ = std::fs::create_dir_all(parent);
                }
                let _ = std::fs::write(&local_path, body);
                state.downloaded_paths.push(path.clone());
                if let Some(h) = remote_hashes.get(path) {
                    state.file_hashes.insert(path.clone(), h.clone());
                }
            }
            Err(e) => return Err(format!("Download {}: {}", path, e)),
        }
        done += 1;
    }

    let mut bytes_uploaded = 0u64;
    let mut uploaded_paths = Vec::new();
    for path in &to_upload {
        set_progress("upload", done, total_work);
        let full = local_root.join(path.replace('/', std::path::MAIN_SEPARATOR_STR));
        if let Ok(meta) = std::fs::metadata(&full) {
            bytes_uploaded += meta.len();
        }
        if let Err(e) = client.upload_file_from_path(path, &full) {
            return Err(format!("Upload {}: {}", path, e));
        }
        uploaded_paths.push(path.clone());
        state.paths.push(path.clone());
        save_sync_state(&state);
        done += 1;
    }

    state.downloaded_paths.clear();
    let final_remote: HashSet<String> = current_remote.difference(&to_del_remote_set).cloned().collect();
    state.paths = final_remote.into_iter().chain(uploaded_paths.into_iter()).collect();
    state.paths.sort();
    save_sync_state(&state);

    set_progress("idle", 0, 0);
    Ok((bytes_downloaded, bytes_uploaded))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    /// Scenario: user had file (in last_synced), deletes it locally; sync must delete from server, not re-download.
    #[test]
    fn delete_local_then_sync_removes_from_server_not_download() {
        let last_synced: HashSet<String> = ["DJI_0011.MP4".to_string()].into_iter().collect();
        let current_local: HashSet<String> = HashSet::new();
        let current_remote: HashSet<String> = ["DJI_0011.MP4".to_string()].into_iter().collect();

        let to_delete_remote: HashSet<String> = last_synced
            .difference(&current_local)
            .filter(|p| !is_ignored(p))
            .cloned()
            .collect();
        assert!(
            to_delete_remote.contains("DJI_0011.MP4"),
            "file deleted locally must be in to_delete_remote so it is removed from server"
        );

        let to_del_remote_set: HashSet<String> = to_delete_remote.iter().cloned().collect();
        let mut to_download: Vec<String> = current_remote
            .difference(&current_local)
            .filter(|p| !is_ignored(p))
            .cloned()
            .collect();
        to_download.retain(|path| !to_del_remote_set.contains(path));
        assert!(
            !to_download.contains(&"DJI_0011.MP4".to_string()),
            "file deleted locally must not be in to_download (must not be re-downloaded)"
        );
    }
}
