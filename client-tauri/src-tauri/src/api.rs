//! HTTP client for Brandy Box backend API. Matches Python client endpoints and behavior.

use serde::{Deserialize, Serialize};
use std::fs::File;
use std::path::Path;
use std::time::Duration;

#[derive(Clone)]
pub struct ApiClient {
    pub base_url: String,
    pub access_token: Option<String>,
}

#[derive(Serialize)]
struct LoginBody {
    email: String,
    password: String,
}

#[derive(Deserialize)]
pub struct LoginResponse {
    pub access_token: String,
    pub refresh_token: String,
    #[serde(rename = "expires_in")]
    pub _expires_in: Option<u64>,
}

#[derive(Serialize)]
struct RefreshBody {
    refresh_token: String,
}

#[derive(Serialize)]
struct ChangePasswordBody {
    current_password: String,
    new_password: String,
}

#[derive(Deserialize)]
pub struct User {
    pub email: String,
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub is_admin: Option<bool>,
    pub storage_limit_bytes: Option<i64>,
}

#[derive(Deserialize)]
pub struct StorageInfo {
    pub used_bytes: i64,
    pub limit_bytes: Option<i64>,
    /// Total bytes on the server (Pi) filesystem containing storage. Optional for backward compatibility.
    #[serde(default)]
    pub server_disk_total_bytes: Option<i64>,
    /// Used bytes on that filesystem (total - free). Optional for backward compatibility.
    #[serde(default)]
    pub server_disk_used_bytes: Option<i64>,
    /// Path that was used for server disk stats (for debugging).
    #[serde(default)]
    pub server_disk_path: Option<String>,
}

#[derive(Deserialize)]
pub struct FileItem {
    pub path: String,
    pub mtime: f64,
    pub hash: Option<String>,
}

#[derive(Serialize)]
struct CreateUserBody {
    email: String,
    first_name: String,
    last_name: String,
}

#[derive(Serialize)]
struct UpdateUserBody {
    storage_limit_bytes: Option<i64>,
}

impl ApiClient {
    pub fn new(base_url: String) -> Self {
        ApiClient { base_url, access_token: None }
    }

    pub fn set_access_token(&mut self, token: Option<String>) {
        self.access_token = token;
    }

    fn client(&self) -> reqwest::blocking::Client {
        reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .expect("http client")
    }

    /// Client for binary download: long timeout, no gzip/deflate so response body is raw bytes
    /// (avoids "error decoding response body" when server or proxy sends compressed binary).
    fn download_client(&self) -> reqwest::blocking::Client {
        reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(600))
            .no_gzip()
            .no_deflate()
            .build()
            .expect("http client")
    }

    fn headers(&self) -> reqwest::header::HeaderMap {
        let mut h = reqwest::header::HeaderMap::new();
        h.insert(reqwest::header::ACCEPT, "application/json".parse().unwrap());
        if let Some(t) = &self.access_token {
            let v = format!("Bearer {}", t);
            h.insert(reqwest::header::AUTHORIZATION, v.parse().unwrap());
        }
        h
    }

    pub fn login(&self, email: &str, password: &str) -> Result<LoginResponse, String> {
        let url = format!("{}/api/auth/login", self.base_url.trim_end_matches('/'));
        let body = LoginBody { email: email.to_string(), password: password.to_string() };
        let r = self
            .client()
            .post(&url)
            .json(&body)
            .header("Content-Type", "application/json")
            .send()
            .map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            let status = r.status();
            let text = r.text().unwrap_or_default();
            return Err(format!("{} {}", status, text));
        }
        r.json().map_err(|e| e.to_string())
    }

    pub fn refresh(&self, refresh_token: &str) -> Result<LoginResponse, String> {
        let url = format!("{}/api/auth/refresh", self.base_url.trim_end_matches('/'));
        let body = RefreshBody { refresh_token: refresh_token.to_string() };
        let r = self
            .client()
            .post(&url)
            .json(&body)
            .header("Content-Type", "application/json")
            .send()
            .map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            let status = r.status();
            let text = r.text().unwrap_or_default();
            return Err(format!("{} {}", status, text));
        }
        r.json().map_err(|e| e.to_string())
    }

    pub fn me(&self) -> Result<User, String> {
        let url = format!("{}/api/users/me", self.base_url.trim_end_matches('/'));
        let r = self.client().get(&url).headers(self.headers()).send().map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            return Err(format!("{}", r.status()));
        }
        r.json().map_err(|e| e.to_string())
    }

    pub fn change_password(&self, current: &str, new_pass: &str) -> Result<(), String> {
        let url = format!("{}/api/auth/change-password", self.base_url.trim_end_matches('/'));
        let body = ChangePasswordBody { current_password: current.to_string(), new_password: new_pass.to_string() };
        let r = self
            .client()
            .post(&url)
            .headers(self.headers())
            .json(&body)
            .header("Content-Type", "application/json")
            .send()
            .map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            return Err(format!("{}", r.status()));
        }
        Ok(())
    }

    pub fn get_storage(&self) -> Result<StorageInfo, String> {
        let url = format!("{}/api/files/storage", self.base_url.trim_end_matches('/'));
        let r = self.client().get(&url).headers(self.headers()).send().map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            return Err(format!("{}", r.status()));
        }
        r.json().map_err(|e| e.to_string())
    }

    pub fn list_files(&self) -> Result<Vec<FileItem>, String> {
        let url = format!("{}/api/files/list", self.base_url.trim_end_matches('/'));
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(60))
            .build()
            .expect("client");
        let r = client.get(&url).headers(self.headers()).send().map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            return Err(format!("{}", r.status()));
        }
        r.json().map_err(|e| e.to_string())
    }

    /// Upload file from disk with retries. For files > 50MB, uses chunked upload to bypass
    /// proxy body limits (e.g. Cloudflare 100MB).
    pub fn upload_file_from_path(&self, path: &str, local_path: &Path) -> Result<(), String> {
        let file_size = std::fs::metadata(local_path).map_err(|e| e.to_string())?.len();

        if file_size > 50 * 1024 * 1024 {
            return self.upload_file_chunked(path, local_path, file_size);
        }

        let url = format!("{}/api/files/upload", self.base_url.trim_end_matches('/'));
        let url = format!("{}?path={}", url, urlencoding::encode(path));
        let timeout_secs = 600 + (file_size / (1024 * 1024)).min(100) * 30;
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(timeout_secs))
            .tcp_keepalive(Duration::from_secs(60))
            .build()
            .expect("http client");

        let mut last_err = String::new();
        for attempt in 0..3 {
            let file = File::open(local_path).map_err(|e| e.to_string())?;
            let body = reqwest::blocking::Body::sized(file, file_size);
            let mut headers = self.headers();
            headers.insert(
                reqwest::header::CONTENT_TYPE,
                "application/octet-stream".parse().unwrap(),
            );
            match client.post(&url).headers(headers).body(body).send() {
                Ok(r) => {
                    if !r.status().is_success() {
                        let status = r.status();
                        let body_text = r.text().unwrap_or_default();
                        last_err = if body_text.trim().is_empty() {
                            format!("{}", status)
                        } else {
                            format!("{}: {}", status, body_text.trim())
                        };
                    } else {
                        return Ok(());
                    }
                }
                Err(e) => {
                    last_err = e.to_string();
                }
            }
            if attempt < 2 {
                std::thread::sleep(Duration::from_secs(3 + attempt as u64 * 4));
            }
        }
        Err(last_err)
    }

    fn upload_file_chunked(&self, path: &str, local_path: &Path, file_size: u64) -> Result<(), String> {
        let base = self.base_url.trim_end_matches('/');
        let init_url = format!("{}/api/files/upload/init?path={}", base, urlencoding::encode(path));

        let resp = self.client()
            .post(&init_url)
            .headers(self.headers())
            .send()
            .map_err(|e| format!("init failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("init failed: {}", resp.status()));
        }

        let init_data: serde_json::Value = resp.json().map_err(|e| e.to_string())?;
        let upload_id = init_data["upload_id"].as_str().ok_or("no upload_id")?;

        let chunk_size = 20 * 1024 * 1024; // 20MB chunks
        let mut file = File::open(local_path).map_err(|e| e.to_string())?;
        use std::io::{Read, Seek, SeekFrom};

        let mut index = 0;
        let mut offset = 0;

        while offset < file_size {
            let current_chunk_size = std::cmp::min(chunk_size, file_size - offset);
            let mut buffer = vec![0; current_chunk_size as usize];
            file.seek(SeekFrom::Start(offset)).map_err(|e| e.to_string())?;
            file.read_exact(&mut buffer).map_err(|e| e.to_string())?;

            let chunk_url = format!("{}/api/files/upload/chunk?upload_id={}&index={}", base, upload_id, index);

            let mut last_err = String::new();
            let mut success = false;
            for attempt in 0..3 {
                let mut headers = self.headers();
                headers.insert(reqwest::header::CONTENT_TYPE, "application/octet-stream".parse().unwrap());

                match self.client().post(&chunk_url).headers(headers).body(buffer.clone()).send() {
                    Ok(r) if r.status().is_success() => {
                        success = true;
                        break;
                    }
                    Ok(r) => last_err = format!("chunk {} failed: {}", index, r.status()),
                    Err(e) => last_err = format!("chunk {} failed: {}", index, e),
                }
                if attempt < 2 {
                    std::thread::sleep(Duration::from_secs(2 * (attempt + 1) as u64));
                }
            }

            if !success {
                return Err(last_err);
            }

            offset += current_chunk_size;
            index += 1;
        }

        let finalize_url = format!("{}/api/files/upload/finalize?upload_id={}", base, upload_id);
        let resp = self.client()
            .post(&finalize_url)
            .headers(self.headers())
            .send()
            .map_err(|e| format!("finalize failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("finalize failed: {}", resp.status()));
        }

        Ok(())
    }

    /// Upload in-memory body (used when caller already has bytes). For large files prefer upload_file_from_path.
    #[allow(dead_code)]
    pub fn upload_file(&self, path: &str, body: &[u8]) -> Result<(), String> {
        let url = format!("{}/api/files/upload", self.base_url.trim_end_matches('/'));
        let url = format!("{}?path={}", url, urlencoding::encode(path));
        let timeout_secs = 600 + (body.len() as u64 / (1024 * 1024)).min(1200) * 60;
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(timeout_secs))
            .build()
            .expect("http client");
        let mut headers = self.headers();
        headers.insert(
            reqwest::header::CONTENT_TYPE,
            "application/octet-stream".parse().unwrap(),
        );
        let r = client
            .post(&url)
            .headers(headers)
            .body(body.to_vec())
            .send()
            .map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            let status = r.status();
            let body_text = r.text().unwrap_or_default();
            return Err(if body_text.trim().is_empty() {
                format!("{}", status)
            } else {
                format!("{}: {}", status, body_text.trim())
            });
        }
        Ok(())
    }

    /// Download file with retries, streaming directly to a temporary file to save memory.
    /// Returns the bytes of the file for compatibility with existing sync logic.
    pub fn download_file(&self, path: &str) -> Result<Vec<u8>, String> {
        let base = self.base_url.trim_end_matches('/');
        let url = format!("{}/api/files/download?path={}", base, urlencoding::encode(path));
        let mut last_err = String::new();

        for attempt in 0..3 {
            match self.download_client().get(&url).headers(self.headers()).send() {
                Ok(mut r) => {
                    if !r.status().is_success() {
                        let status = r.status();
                        let resp_body = r.text().unwrap_or_default();
                        last_err = if resp_body.trim().is_empty() {
                            format!("{}", status)
                        } else {
                            format!("{}: {}", status, resp_body.trim())
                        };
                    } else {
                        // Create a temporary file to stream the response into
                        let tmp_file_path = std::env::temp_dir().join(format!("bb_dl_{}", uuid::Uuid::new_v4()));
                        let mut tmp_file = File::create(&tmp_file_path).map_err(|e| e.to_string())?;

                        if let Err(e) = r.copy_to(&mut tmp_file) {
                            let _ = std::fs::remove_file(&tmp_file_path);
                            last_err = format!("failed to read response body: {}", e);
                        } else {
                            // Read from temp file into Vec<u8> (still memory-intensive but respects streaming from network)
                            // In a full refactor, sync.rs should handle the file path directly.
                            let mut buf = Vec::new();
                            let mut read_file = File::open(&tmp_file_path).map_err(|e| e.to_string())?;
                            use std::io::Read;
                            read_file.read_to_end(&mut buf).map_err(|e| e.to_string())?;
                            let _ = std::fs::remove_file(&tmp_file_path);
                            return Ok(buf);
                        }
                    }
                }
                Err(e) => {
                    last_err = e.to_string();
                }
            }
            if attempt < 2 {
                std::thread::sleep(Duration::from_secs(2 * (attempt + 1)));
            }
        }
        Err(last_err)
    }

    pub fn delete_file(&self, path: &str) -> Result<(), String> {
        let base = self.base_url.trim_end_matches('/');
        let url = format!("{}/api/files/delete?path={}", base, urlencoding::encode(path));
        let r = self.client().delete(&url).headers(self.headers()).send().map_err(|e| e.to_string())?;
        if r.status().as_u16() == 404 {
            return Ok(());
        }
        if !r.status().is_success() {
            return Err(format!("{}", r.status()));
        }
        Ok(())
    }

    pub fn list_users(&self) -> Result<Vec<User>, String> {
        let url = format!("{}/api/users", self.base_url.trim_end_matches('/'));
        let r = self.client().get(&url).headers(self.headers()).send().map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            return Err(format!("{}", r.status()));
        }
        r.json().map_err(|e| e.to_string())
    }

    pub fn create_user(&self, email: &str, first_name: &str, last_name: &str) -> Result<serde_json::Value, String> {
        let url = format!("{}/api/users", self.base_url.trim_end_matches('/'));
        let body = CreateUserBody {
            email: email.to_string(),
            first_name: first_name.to_string(),
            last_name: last_name.to_string(),
        };
        let r = self
            .client()
            .post(&url)
            .headers(self.headers())
            .json(&body)
            .header("Content-Type", "application/json")
            .send()
            .map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            return Err(format!("{}", r.status()));
        }
        r.json().map_err(|e| e.to_string())
    }

    pub fn update_user_storage_limit(&self, email: &str, limit_bytes: Option<i64>) -> Result<serde_json::Value, String> {
        let encoded = urlencoding::encode(email);
        let url = format!("{}/api/users/{}", self.base_url.trim_end_matches('/'), encoded);
        let body = UpdateUserBody { storage_limit_bytes: limit_bytes };
        let r = self
            .client()
            .patch(&url)
            .headers(self.headers())
            .json(&body)
            .header("Content-Type", "application/json")
            .send()
            .map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            return Err(format!("{}", r.status()));
        }
        r.json().map_err(|e| e.to_string())
    }

    /// Report client version and last sync outcome to the server (best-effort).
    pub fn client_ping(&self, last_sync_ok: Option<bool>, last_sync_at_rfc3339: Option<String>) -> Result<(), String> {
        let url = format!("{}/api/clients/ping", self.base_url.trim_end_matches('/'));
        let body = serde_json::json!({
            "client_type": "tauri",
            "client_version": env!("CARGO_PKG_VERSION"),
            "last_sync_ok": last_sync_ok,
            "last_sync_at": last_sync_at_rfc3339,
        });
        let r = self
            .client()
            .post(&url)
            .headers(self.headers())
            .json(&body)
            .header("Content-Type", "application/json")
            .send()
            .map_err(|e| e.to_string())?;
        if r.status() == reqwest::StatusCode::NO_CONTENT || r.status().is_success() {
            return Ok(());
        }
        Err(format!("{}", r.status()))
    }

    pub fn delete_user(&self, email: &str) -> Result<(), String> {
        let encoded = urlencoding::encode(email);
        let url = format!("{}/api/users/{}", self.base_url.trim_end_matches('/'), encoded);
        let r = self.client().delete(&url).headers(self.headers()).send().map_err(|e| e.to_string())?;
        if !r.status().is_success() {
            return Err(format!("{}", r.status()));
        }
        Ok(())
    }
}
