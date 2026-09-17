//! Sync engine: list local/remote, diff, propagate deletes, download, upload.
//! Matches Python client logic (robust sync v2) and sync_state.json layout.
//!
//! Robustness: only mark paths as "in sync" when verified on both sides.
//! Skipped downloads/uploads are excluded from state and trigger warning status.

use crate::api::ApiClient;
use crate::config;
use sha2::{Digest, Sha256};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::Path;

const SYNC_IGNORE: &[&str] = &[".directory", "Thumbs.db", "Desktop.ini", ".DS_Store"];

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

fn compute_file_hash(path: &Path) -> Option<String> {
    let mut file = std::fs::File::open(path).ok()?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 65536]; // 64KB buffer
    use std::io::Read;
    loop {
        let n = file.read(&mut buffer).ok()?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }
    Some(format!("{:x}", hasher.finalize()))
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
    Warning(String),
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
        SyncStatus::Warning(msg) => ("warning".to_string(), Some(msg.clone())),
        SyncStatus::Error(msg) => ("error".to_string(), Some(msg.clone())),
    }
}

/// Payload for the sync-status Tauri event (status + optional message).
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

pub fn classify_error(err_str: &str) -> &'static str {
    let lower = err_str.to_lowercase();
    if lower.contains("524") {
        "CLOUDFLARE_524"
    } else if lower.contains("401") || lower.contains("403") || lower.contains("unauthorized") || lower.contains("forbidden") {
        "AUTH_FAILED"
    } else if lower.contains("404") || lower.contains("not found") {
        "NOT_FOUND"
    } else if lower.contains("413") || lower.contains("too large") {
        "PAYLOAD_TOO_LARGE"
    } else if lower.contains("timeout") || lower.contains("timed out") {
        "NETWORK_TIMEOUT"
    } else if lower.contains("permission denied") || lower.contains("os error 13") || lower.contains("access is denied") {
        "IO_PERMISSION_DENIED"
    } else if lower.contains("hash mismatch") || lower.contains("checksum") {
        "HASH_MISMATCH"
    } else if lower.contains("connection refused") {
        "CONNECTION_REFUSED"
    } else {
        "SYNC_ERROR"
    }
}

const MAX_QUEUE_ITEMS: usize = 200;

pub fn load_telemetry_queue() -> crate::api::TelemetryBatchPayload {
    let path = config::get_telemetry_queue_path();
    if !path.exists() {
        return crate::api::TelemetryBatchPayload::default();
    }
    if let Ok(content) = std::fs::read_to_string(&path) {
        if let Ok(queue) = serde_json::from_str(&content) {
            return queue;
        }
    }
    crate::api::TelemetryBatchPayload::default()
}

pub fn save_telemetry_queue(queue: &crate::api::TelemetryBatchPayload) {
    let path = config::get_telemetry_queue_path();
    let _ = std::fs::create_dir_all(path.parent().unwrap_or(Path::new(".")));
    let _ = std::fs::write(path, serde_json::to_string_pretty(queue).unwrap_or_default());
}

pub fn enqueue_diagnostic_event(event: crate::api::DiagnosticEventPayload) {
    let mut queue = load_telemetry_queue();
    queue.events.push(event);
    if queue.events.len() > MAX_QUEUE_ITEMS {
        let drain_count = queue.events.len() - MAX_QUEUE_ITEMS;
        queue.events.drain(0..drain_count);
    }
    save_telemetry_queue(&queue);
}

pub fn enqueue_sync_summary(summary: crate::api::SyncSummaryPayload) {
    let mut queue = load_telemetry_queue();
    queue.summaries.push(summary);
    if queue.summaries.len() > MAX_QUEUE_ITEMS {
        let drain_count = queue.summaries.len() - MAX_QUEUE_ITEMS;
        queue.summaries.drain(0..drain_count);
    }
    save_telemetry_queue(&queue);
}

pub fn flush_telemetry_queue(client: &ApiClient) -> Result<(), String> {
    let queue = load_telemetry_queue();
    if queue.events.is_empty() && queue.summaries.is_empty() {
        return Ok(());
    }
    match client.post_telemetry_events(&queue) {
        Ok(()) => {
            save_telemetry_queue(&crate::api::TelemetryBatchPayload::default());
            log::info!(
                "Flushed {} telemetry events and {} summaries to backend",
                queue.events.len(),
                queue.summaries.len()
            );
            Ok(())
        }
        Err(e) => {
            log::warn!("Failed to flush telemetry batch (buffered offline): {}", e);
            Err(e)
        }
    }
}


pub fn run_sync(client: &mut ApiClient, local_root: &Path) -> Result<(u64, u64, Option<String>), String> {
    let trace_id = match &client.sync_id {
        Some(tid) => tid.clone(),
        None => {
            let tid = crate::api::generate_trace_id();
            client.set_sync_id(Some(tid.clone()));
            tid
        }
    };
    let started_at = chrono::Utc::now().to_rfc3339();
    let start_instant = std::time::Instant::now();

    // Flush any pending events from previous offline runs
    let _ = flush_telemetry_queue(client);

    let mut state = load_sync_state();
    let last_synced: HashSet<String> = state.paths.iter().cloned().collect();
    let prev_downloaded: HashSet<String> = state.downloaded_paths.iter().cloned().collect();

    set_progress("listing", 0, 0);
    let local_list = list_local(local_root);
    let remote_list = match client.list_files() {
        Ok(list) => list,
        Err(e) => {
            let err_code = classify_error(&e);
            enqueue_diagnostic_event(crate::api::DiagnosticEventPayload {
                trace_id: Some(trace_id.clone()),
                created_at: Some(chrono::Utc::now().to_rfc3339()),
                client_type: config::get_client_type().to_string(),
                device_name: config::get_device_name(),
                level: "ERROR".to_string(),
                category: "sync.list".to_string(),
                error_code: err_code.to_string(),
                message: format!("List remote files failed: {}", e),
                context_json: None,
            });
            enqueue_sync_summary(crate::api::SyncSummaryPayload {
                trace_id: trace_id.clone(),
                client_type: config::get_client_type().to_string(),
                client_version: env!("CARGO_PKG_VERSION").to_string(),
                device_name: config::get_device_name(),
                started_at: started_at.clone(),
                completed_at: Some(chrono::Utc::now().to_rfc3339()),
                duration_ms: start_instant.elapsed().as_millis() as i64,
                status: "failed".to_string(),
                files_scanned: local_list.len() as i64,
                files_uploaded: 0,
                files_downloaded: 0,
                failure_count: 1,
                bytes_transferred: 0,
                error_summary_json: Some(serde_json::json!({ "error": e }).to_string()),
            });
            let _ = flush_telemetry_queue(client);
            return Err(e);
        }
    };


    log::info!(
        "Sync: {} remote, {} local (sync_folder={})",
        remote_list.len(),
        local_list.len(),
        local_root.display()
    );

    let local_by_path: HashMap<String, f64> = local_list.iter().cloned().collect();
    let remote_by_path: HashMap<String, f64> = remote_list.iter().map(|i| (i.path.clone(), i.mtime)).collect();
    let remote_hashes: HashMap<String, String> = remote_list.iter().filter_map(|i| i.hash.clone().map(|h| (i.path.clone(), h))).collect();
    let remote_by_item: HashMap<String, &crate::api::FileItem> = remote_list.iter().map(|i| (i.path.clone(), i)).collect();

    let current_local: HashSet<String> = local_by_path.keys().cloned().collect();
    let current_remote: HashSet<String> = remote_by_path.keys().cloned().collect();

    let mut to_delete_remote: HashSet<String> = last_synced.difference(&current_local).filter(|p| !is_ignored(p)).cloned().collect();

    // Safety: never delete more files on server than we have locally when the number is large
    if to_delete_remote.len() > 50 && to_delete_remote.len() > current_local.len() {
        log::warn!(
            "Skipping server deletes: would delete {} on server but only {} files locally; likely new device or wrong sync folder",
            to_delete_remote.len(),
            current_local.len()
        );
        to_delete_remote.clear();
    }

    let to_delete_local: HashSet<String> = last_synced.difference(&current_remote).cloned().collect();

    let mut to_del_remote: Vec<String> = to_delete_remote.into_iter().collect();
    to_del_remote.sort_by(|a, b| b.matches('/').count().cmp(&a.matches('/').count()));

    let mut to_del_local: Vec<String> = to_delete_local.into_iter().collect();
    to_del_local.sort_by(|a, b| b.matches('/').count().cmp(&a.matches('/').count()));

    let to_del_local_set: HashSet<String> = to_del_local.iter().cloned().collect();
    let to_del_remote_set: HashSet<String> = to_del_remote.iter().cloned().collect();

    let total_work = to_del_remote.len() + to_del_local.len()
        + current_remote.difference(&current_local).filter(|p| !is_ignored(p)).count()
        + current_local.difference(&current_remote).filter(|p| !is_ignored(p)).count();
    let total_work = total_work as u64;
    let mut done = 0u64;

    for path in &to_del_remote {
        set_progress("delete_server", done, total_work);
        if let Err(e) = client.delete_file(path) {
            let err_code = classify_error(&e);
            enqueue_diagnostic_event(crate::api::DiagnosticEventPayload {
                trace_id: Some(trace_id.clone()),
                created_at: Some(chrono::Utc::now().to_rfc3339()),
                client_type: config::get_client_type().to_string(),
                device_name: config::get_device_name(),
                level: "ERROR".to_string(),
                category: "sync.delete".to_string(),
                error_code: err_code.to_string(),
                message: format!("Delete server {}: {}", path, e),
                context_json: Some(serde_json::json!({ "path": path }).to_string()),
            });
            return Err(format!("Delete server {}: {}", path, e));
        }
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

    let remaining_local: HashSet<String> = current_local.difference(&to_del_local_set).cloned().collect();
    let remaining_remote: HashSet<String> = current_remote.difference(&to_del_remote_set).cloned().collect();
    let base_synced: HashSet<String> = remaining_local.intersection(&remaining_remote).filter(|p| !is_ignored(p)).cloned().collect();

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
                if let Some(server_hash) = remote_hashes.get(path) {
                    let local_path = local_root.join(path.replace('/', std::path::MAIN_SEPARATOR_STR));
                    if local_path.exists() && local_path.is_file() {
                        if let Some(local_hash) = compute_file_hash(&local_path) {
                            if local_hash == *server_hash {
                                state.file_hashes.insert(path.clone(), server_hash.clone());
                                continue;
                            }
                        }
                    }
                }
                to_download.push(path.clone());
            }
        }
    }
    to_download.sort();
    to_download.dedup();

    // Build to_upload with hash-based skip when local matches server (avoids clock skew)
    let to_upload: Vec<String> = local_list
        .iter()
        .filter(|(path, _)| !is_ignored(path))
        .filter(|(path, local_mtime)| {
            let remote = remote_by_item.get(path);
            match remote {
                None => true,
                Some(r) => {
                    if *local_mtime <= r.mtime {
                        return false;
                    }
                    if let Some(server_hash) = &r.hash {
                        let local_path = local_root.join(path.replace('/', std::path::MAIN_SEPARATOR_STR));
                        if local_path.exists() && local_path.is_file() {
                            if let Some(local_hash) = compute_file_hash(&local_path) {
                                if local_hash == *server_hash {
                                    return false;
                                }
                            }
                        }
                    }
                    true
                }
            }
        })
        .map(|(path, _)| path.clone())
        .collect();

    log::info!(
        "Sync plan: {} to_download, {} to_upload, {} delete_server, {} delete_local",
        to_download.len(),
        to_upload.len(),
        to_del_remote.len(),
        to_del_local.len()
    );

    let mut bytes_downloaded = 0u64;
    let mut completed_downloads: HashSet<String> = HashSet::new();
    let mut skipped_downloads: HashSet<String> = HashSet::new();

    let mut bytes_uploaded = 0u64;
    let mut completed_uploads: HashSet<String> = HashSet::new();
    let mut skipped_uploads: HashSet<String> = HashSet::new();

    let persist_current_state = |state: &mut SyncStateFile, base_synced: &HashSet<String>, completed_downloads: &HashSet<String>, completed_uploads: &HashSet<String>| {
        let new_synced: HashSet<String> = base_synced
            .union(completed_downloads)
            .cloned()
            .chain(completed_uploads.iter().cloned())
            .collect();
        let mut new_synced: Vec<String> = new_synced.into_iter().collect();
        new_synced.sort();
        state.paths = new_synced;
        save_sync_state(state);
    };

    let mut download_counter = 0usize;
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
        match client.download_file_to_path(path, &local_path) {
            Ok(bytes) => {
                bytes_downloaded += bytes;
                completed_downloads.insert(path.clone());
                if let Some(h) = remote_hashes.get(path) {
                    state.file_hashes.insert(path.clone(), h.clone());
                }
                download_counter += 1;
                if download_counter % 50 == 0 {
                    persist_current_state(&mut state, &base_synced, &completed_downloads, &completed_uploads);
                }
            }
            Err(e) => {
                let err_code = classify_error(&e);
                enqueue_diagnostic_event(crate::api::DiagnosticEventPayload {
                    trace_id: Some(trace_id.clone()),
                    created_at: Some(chrono::Utc::now().to_rfc3339()),
                    client_type: config::get_client_type().to_string(),
                    device_name: config::get_device_name(),
                    level: if e.contains("404") { "WARN".to_string() } else { "ERROR".to_string() },
                    category: "sync.download".to_string(),
                    error_code: err_code.to_string(),
                    message: format!("Download {}: {}", path, e),
                    context_json: Some(serde_json::json!({ "path": path }).to_string()),
                });
                if e.contains("404") {
                    log::debug!("Download {}: 404, file no longer on server", path);
                    if local_path.exists() && local_path.is_file() {
                        let _ = std::fs::remove_file(&local_path);
                    }
                } else {
                    log::warn!("Download {}: {}, skipping file for this cycle", path, e);
                }
                skipped_downloads.insert(path.clone());
            }
        }
        done += 1;
    }

    if !skipped_downloads.is_empty() {
        let sample: Vec<_> = {
            let mut v: Vec<_> = skipped_downloads.iter().cloned().collect();
            v.sort();
            v.into_iter().take(5).collect()
        };
        log::warn!(
            "Skipped {} downloads (error, permission denied or file gone): sample={:?}",
            skipped_downloads.len(),
            sample
        );
    }

    let mut upload_counter = 0usize;
    for path in &to_upload {
        set_progress("upload", done, total_work);
        let full = local_root.join(path.replace('/', std::path::MAIN_SEPARATOR_STR));
        if full.exists() && full.is_file() {
            let file_len = std::fs::metadata(&full).map(|m| m.len()).unwrap_or(0);
            match client.upload_file_from_path(path, &full) {
                Ok(()) => {
                    bytes_uploaded += file_len;
                    completed_uploads.insert(path.clone());
                    upload_counter += 1;
                    if upload_counter % 25 == 0 {
                        persist_current_state(&mut state, &base_synced, &completed_downloads, &completed_uploads);
                    }
                }
                Err(e) => {
                    let err_code = classify_error(&e);
                    enqueue_diagnostic_event(crate::api::DiagnosticEventPayload {
                        trace_id: Some(trace_id.clone()),
                        created_at: Some(chrono::Utc::now().to_rfc3339()),
                        client_type: config::get_client_type().to_string(),
                        device_name: config::get_device_name(),
                        level: "ERROR".to_string(),
                        category: "sync.upload".to_string(),
                        error_code: err_code.to_string(),
                        message: format!("Upload {}: {}", path, e),
                        context_json: Some(serde_json::json!({ "path": path, "size_bytes": file_len }).to_string()),
                    });
                    log::warn!("Upload {}: {}, skipping file for this cycle", path, e);
                    skipped_uploads.insert(path.clone());
                }
            }
        } else {
            log::debug!("Upload {}: file no longer present, skipping", path);
            skipped_uploads.insert(path.clone());
        }
        done += 1;
    }

    let mut warning_msg = None;
    let mut warnings: Vec<String> = Vec::new();
    if !skipped_downloads.is_empty() {
        warnings.push(format!(
            "{} download(s) skipped (errors, permission denied or file gone on server)",
            skipped_downloads.len()
        ));
    }
    if !skipped_uploads.is_empty() {
        let sample: Vec<_> = {
            let mut v: Vec<_> = skipped_uploads.iter().cloned().collect();
            v.sort();
            v.into_iter().take(5).collect()
        };
        log::warn!(
            "Skipped {} uploads (file no longer present or error during sync): sample={:?}",
            skipped_uploads.len(),
            sample
        );
        warnings.push(format!(
            "{} upload(s) skipped (files removed or upload error during sync)",
            skipped_uploads.len()
        ));
    }
    if !warnings.is_empty() {
        warning_msg = Some(warnings.join("; "));
    }

    // Final state persist
    persist_current_state(&mut state, &base_synced, &completed_downloads, &completed_uploads);
    state.downloaded_paths.clear();
    save_sync_state(&state);

    set_progress("idle", 0, 0);

    let total_failures = (skipped_downloads.len() + skipped_uploads.len()) as i64;
    let summary_status = if total_failures > 0 { "warning".to_string() } else { "ok".to_string() };
    let summary_error_json = if !warnings.is_empty() {
        let sample_downloads: Vec<String> = skipped_downloads.iter().cloned().take(10).collect();
        let sample_uploads: Vec<String> = skipped_uploads.iter().cloned().take(10).collect();
        Some(serde_json::json!({
            "warnings": warnings,
            "skipped_downloads": sample_downloads,
            "skipped_uploads": sample_uploads,
        }).to_string())
    } else {
        None
    };

    enqueue_sync_summary(crate::api::SyncSummaryPayload {
        trace_id: trace_id.clone(),
        client_type: config::get_client_type().to_string(),
        client_version: env!("CARGO_PKG_VERSION").to_string(),
        device_name: config::get_device_name(),
        started_at: started_at.clone(),
        completed_at: Some(chrono::Utc::now().to_rfc3339()),
        duration_ms: start_instant.elapsed().as_millis() as i64,
        status: summary_status,
        files_scanned: (local_list.len() + remote_list.len()) as i64,
        files_uploaded: completed_uploads.len() as i64,
        files_downloaded: completed_downloads.len() as i64,
        failure_count: total_failures,
        bytes_transferred: (bytes_downloaded + bytes_uploaded) as i64,
        error_summary_json: summary_error_json,
    });
    let _ = flush_telemetry_queue(client);

    log::info!(
        "Sync cycle complete: {} downloaded ({} bytes), {} skipped, {} uploaded ({} bytes), {} synced paths{}",
        completed_downloads.len(),
        bytes_downloaded,
        skipped_downloads.len(),
        completed_uploads.len(),
        bytes_uploaded,
        state.paths.len(),
        if warning_msg.is_some() { " [WARNING]" } else { "" }
    );


    Ok((bytes_downloaded, bytes_uploaded, warning_msg))
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

    #[test]
    fn test_error_classification() {
        assert_eq!(classify_error("524 Gateway Timeout"), "CLOUDFLARE_524");
        assert_eq!(classify_error("401 Unauthorized"), "AUTH_FAILED");
        assert_eq!(classify_error("403 Forbidden"), "AUTH_FAILED");
        assert_eq!(classify_error("404 Not Found"), "NOT_FOUND");
        assert_eq!(classify_error("413 Request Entity Too Large"), "PAYLOAD_TOO_LARGE");
        assert_eq!(classify_error("connection timed out after 30s"), "NETWORK_TIMEOUT");
        assert_eq!(classify_error("Permission denied (os error 13)"), "IO_PERMISSION_DENIED");
        assert_eq!(classify_error("hash mismatch expected abc got def"), "HASH_MISMATCH");
        assert_eq!(classify_error("Connection refused"), "CONNECTION_REFUSED");
        assert_eq!(classify_error("unknown disk error"), "SYNC_ERROR");
    }

    #[test]
    fn test_telemetry_queue_persistence() {
        let temp_dir = std::env::temp_dir().join(format!("test_telemetry_{}", uuid::Uuid::new_v4()));
        let _ = std::fs::create_dir_all(&temp_dir);
        let queue_file = temp_dir.join("test_telemetry_queue.json");


        let mut queue = crate::api::TelemetryBatchPayload::default();
        queue.events.push(crate::api::DiagnosticEventPayload {
            trace_id: Some("sync-unit-1".to_string()),
            created_at: Some("2026-09-16T21:00:00Z".to_string()),
            client_type: "desktop-macos".to_string(),
            device_name: "UnitTestDevice".to_string(),
            level: "ERROR".to_string(),
            category: "sync.upload".to_string(),
            error_code: "CLOUDFLARE_524".to_string(),
            message: "Upload timeout test".to_string(),
            context_json: Some("{\"path\":\"test.txt\"}".to_string()),
        });
        queue.summaries.push(crate::api::SyncSummaryPayload {
            trace_id: "sync-unit-1".to_string(),
            client_type: "desktop-macos".to_string(),
            client_version: "1.3.2".to_string(),
            device_name: "UnitTestDevice".to_string(),
            started_at: "2026-09-16T21:00:00Z".to_string(),
            completed_at: Some("2026-09-16T21:01:00Z".to_string()),
            duration_ms: 60000,
            status: "failed".to_string(),
            files_scanned: 10,
            files_uploaded: 0,
            files_downloaded: 0,
            failure_count: 1,
            bytes_transferred: 0,
            error_summary_json: None,
        });

        let json = serde_json::to_string_pretty(&queue).expect("serialize");
        std::fs::write(&queue_file, json).expect("write");

        let loaded_str = std::fs::read_to_string(&queue_file).expect("read");
        let loaded: crate::api::TelemetryBatchPayload = serde_json::from_str(&loaded_str).expect("deserialize");

        assert_eq!(loaded.events.len(), 1);
        assert_eq!(loaded.events[0].error_code, "CLOUDFLARE_524");
        assert_eq!(loaded.summaries.len(), 1);
        assert_eq!(loaded.summaries[0].status, "failed");
    }
}

