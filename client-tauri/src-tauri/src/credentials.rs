//! Keyring-backed credential storage (email + refresh_token). Matches Python keyring usage.
//! When BRANDYBOX_CONFIG_DIR is set (E2E) or when system keyring is unavailable,
//! also supports credentials.json so credentials persist reliably across sessions and platforms.

use crate::config;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

const SERVICE_NAME: &str = "BrandyBox";
const KEY_EMAIL: &str = "email";
const KEY_REFRESH_TOKEN: &str = "refresh_token";
const E2E_CREDENTIALS_FILENAME: &str = "e2e_credentials.json";
const CREDENTIALS_FILENAME: &str = "credentials.json";

fn is_e2e_config() -> bool {
    std::env::var("BRANDYBOX_CONFIG_DIR")
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false)
}

fn service_name() -> &'static str {
    if is_e2e_config() {
        "BrandyBox-E2E"
    } else {
        SERVICE_NAME
    }
}

fn credentials_file_path() -> PathBuf {
    if is_e2e_config() {
        config::get_config_dir().join(E2E_CREDENTIALS_FILENAME)
    } else {
        config::get_config_dir().join(CREDENTIALS_FILENAME)
    }
}

#[derive(Serialize, Deserialize)]
struct CredentialsFile {
    email: String,
    refresh_token: String,
}

fn read_file_credentials() -> Option<(String, String)> {
    let path = credentials_file_path();
    if path.exists() {
        if let Ok(s) = std::fs::read_to_string(&path) {
            if let Ok(f) = serde_json::from_str::<CredentialsFile>(&s) {
                if !f.email.trim().is_empty() && !f.refresh_token.trim().is_empty() {
                    return Some((f.email.trim().to_string(), f.refresh_token.trim().to_string()));
                }
            }
        }
    }
    None
}

fn write_file_credentials(email: &str, refresh_token: &str) {
    let path = credentials_file_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let f = CredentialsFile {
        email: email.to_string(),
        refresh_token: refresh_token.to_string(),
    };
    if let Ok(content) = serde_json::to_string_pretty(&f) {
        let _ = std::fs::write(&path, content);
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600));
        }
    }
}

fn remove_file_credentials() {
    let path = credentials_file_path();
    let _ = std::fs::remove_file(path);
}

fn decode_base64_url(input: &str) -> Option<Vec<u8>> {
    let mut s = input.replace('-', "+").replace('_', "/");
    match s.len() % 4 {
        2 => s.push_str("=="),
        3 => s.push('='),
        _ => {}
    }
    let table = |c: u8| -> Option<u8> {
        match c {
            b'A'..=b'Z' => Some(c - b'A'),
            b'a'..=b'z' => Some(c - b'a' + 26),
            b'0'..=b'9' => Some(c - b'0' + 52),
            b'+' => Some(62),
            b'/' => Some(63),
            _ => None,
        }
    };
    let bytes = s.as_bytes();
    let mut out = Vec::with_capacity(bytes.len() * 3 / 4);
    for chunk in bytes.chunks(4) {
        if chunk.len() < 2 { break; }
        let c0 = table(chunk[0])?;
        let c1 = table(chunk[1])?;
        out.push((c0 << 2) | (c1 >> 4));
        if chunk.len() > 2 && chunk[2] != b'=' {
            let c2 = table(chunk[2])?;
            out.push((c1 << 4) | (c2 >> 2));
            if chunk.len() > 3 && chunk[3] != b'=' {
                let c3 = table(chunk[3])?;
                out.push((c2 << 6) | c3);
            }
        }
    }
    Some(out)
}

pub fn is_jwt_expired(token: &str) -> bool {
    let mut parts = token.split('.');
    let _header = parts.next();
    let Some(payload_b64) = parts.next() else { return false; };
    let Some(sig) = parts.next() else { return false; };
    if parts.next().is_some() || sig.is_empty() { return false; }
    let Some(payload_bytes) = decode_base64_url(payload_b64) else { return false; };
    if let Ok(val) = serde_json::from_slice::<serde_json::Value>(&payload_bytes) {
        if let Some(exp) = val.get("exp").and_then(|e| e.as_i64()) {
            let now = chrono::Utc::now().timestamp();
            return exp <= now;
        }
    }
    false
}

pub fn get_stored() -> Option<(String, String)> {
    if is_e2e_config() || cfg!(target_os = "macos") {
        if let Some((email, token)) = read_file_credentials() {
            if !is_jwt_expired(&token) {
                return Some((email, token));
            }
        }
        return None;
    }
    // Check credentials.json first (fast, reliable, never prompts or hangs)
    if let Some((email, token)) = read_file_credentials() {
        if !is_jwt_expired(&token) {
            return Some((email, token));
        }
    }
    let service = service_name();
    let keyring_email = keyring::Entry::new(service, KEY_EMAIL).ok().and_then(|e| e.get_password().ok());
    let keyring_token = keyring::Entry::new(service, KEY_REFRESH_TOKEN).ok().and_then(|e| e.get_password().ok());
    if let (Some(email), Some(token)) = (keyring_email, keyring_token) {
        if !email.trim().is_empty() && !token.trim().is_empty() && !is_jwt_expired(&token) {
            write_file_credentials(&email, &token);
            return Some((email.trim().to_string(), token.trim().to_string()));
        }
    }
    None
}

pub fn set_stored(email: &str, refresh_token: &str) {
    if is_e2e_config() || cfg!(target_os = "macos") {
        write_file_credentials(email, refresh_token);
        return;
    }
    let service = service_name();
    let _ = keyring::Entry::new(service, KEY_EMAIL).and_then(|e| e.set_password(email));
    let _ = keyring::Entry::new(service, KEY_REFRESH_TOKEN).and_then(|e| e.set_password(refresh_token));
    // Also save to credentials.json as a fallback if keyring fails or is unavailable
    write_file_credentials(email, refresh_token);
}

pub fn clear_stored() {
    if is_e2e_config() || cfg!(target_os = "macos") {
        remove_file_credentials();
        return;
    }
    let service = service_name();
    let _ = keyring::Entry::new(service, KEY_EMAIL).and_then(|e| e.delete_credential());
    let _ = keyring::Entry::new(service, KEY_REFRESH_TOKEN).and_then(|e| e.delete_credential());
    remove_file_credentials();
}

#[cfg(test)]
mod tests {
    use super::*;
    static TEST_MUTEX: std::sync::Mutex<()> = std::sync::Mutex::new(());

    #[test]
    fn test_store_and_get() {
        let _lock = TEST_MUTEX.lock().unwrap();
        let temp_dir = std::env::temp_dir().join(format!("brandybox_test_{}", uuid::Uuid::new_v4()));
        std::env::set_var("BRANDYBOX_CONFIG_DIR", &temp_dir);
        clear_stored();
        set_stored("test@example.com", "dummy_token_123");
        let res = get_stored();
        assert_eq!(res, Some(("test@example.com".to_string(), "dummy_token_123".to_string())));
        clear_stored();
        assert_eq!(get_stored(), None);
        std::env::remove_var("BRANDYBOX_CONFIG_DIR");
        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_jwt_expiration() {
        // Not a JWT
        assert!(!is_jwt_expired("not_a_jwt"));
        // Expired JWT: exp = 1000 (past)
        // {"exp":1000} base64url is eyJleHAiOjEwMDB9
        let expired_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjEwMDB9.signature";
        assert!(is_jwt_expired(expired_jwt));
        // Valid future JWT: exp = 9999999999 (future)
        // {"exp":9999999999} base64url is eyJleHAiOjk5OTk5OTk5OTl9
        let valid_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjk5OTk5OTk5OTl9.signature";
        assert!(!is_jwt_expired(valid_jwt));
    }

    #[test]
    fn test_get_stored_expired_token() {
        let _lock = TEST_MUTEX.lock().unwrap();
        let temp_dir = std::env::temp_dir().join(format!("brandybox_test_{}", uuid::Uuid::new_v4()));
        std::env::set_var("BRANDYBOX_CONFIG_DIR", &temp_dir);
        clear_stored();
        let expired_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjEwMDB9.signature";
        set_stored("test@example.com", expired_jwt);
        let res = get_stored();
        assert_eq!(res, None, "Expired token should return None from get_stored");
        clear_stored();
        std::env::remove_var("BRANDYBOX_CONFIG_DIR");
        let _ = std::fs::remove_dir_all(&temp_dir);
    }
}

