//! HTTP client for Brandy Box backend API. Matches Python client endpoints and behavior.

use serde::{Deserialize, Serialize};
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

    /// Client for binary download: long timeout so large files (e.g. MP4) can finish.
    fn download_client(&self) -> reqwest::blocking::Client {
        reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(600))
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

    /// Upload file with retries. Large uploads (e.g. MP4) can hit connection resets; retrying often succeeds.
    pub fn upload_file(&self, path: &str, body: &[u8]) -> Result<(), String> {
        let url = format!("{}/api/files/upload", self.base_url.trim_end_matches('/'));
        let url = format!("{}?path={}", url, urlencoding::encode(path));
        let timeout_secs = 600 + (body.len() as u64 / (1024 * 1024)).min(1200) * 60;
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(timeout_secs))
            .build()
            .expect("http client");
        let body_copy = body.to_vec();
        let mut last_err = String::new();
        for attempt in 0..3 {
            let mut headers = self.headers();
            headers.insert(
                reqwest::header::CONTENT_TYPE,
                "application/octet-stream".parse().unwrap(),
            );
            match client
                .post(&url)
                .headers(headers)
                .body(body_copy.clone())
                .send()
            {
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
                std::thread::sleep(Duration::from_secs(2 * (attempt + 1)));
            }
        }
        Err(last_err)
    }

    /// Download file with retries. Large downloads can hit connection resets; retrying often succeeds.
    pub fn download_file(&self, path: &str) -> Result<Vec<u8>, String> {
        let base = self.base_url.trim_end_matches('/');
        let url = format!("{}/api/files/download?path={}", base, urlencoding::encode(path));
        let mut last_err = String::new();
        for attempt in 0..3 {
            match self
                .download_client()
                .get(&url)
                .headers(self.headers())
                .send()
            {
                Ok(r) => {
                    if !r.status().is_success() {
                        let status = r.status();
                        let resp_body = r.text().unwrap_or_default();
                        last_err = if resp_body.trim().is_empty() {
                            format!("{}", status)
                        } else {
                            format!("{}: {}", status, resp_body.trim())
                        };
                    } else if let Ok(bytes) = r.bytes().map(|b| b.to_vec()) {
                        return Ok(bytes);
                    } else {
                        last_err = "failed to read response body".to_string();
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
