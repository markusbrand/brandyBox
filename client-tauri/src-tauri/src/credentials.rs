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

pub fn get_stored() -> Option<(String, String)> {
    if is_e2e_config() {
        return read_file_credentials();
    }
    let service = service_name();
    let keyring_email = keyring::Entry::new(service, KEY_EMAIL).ok().and_then(|e| e.get_password().ok());
    let keyring_token = keyring::Entry::new(service, KEY_REFRESH_TOKEN).ok().and_then(|e| e.get_password().ok());
    if let (Some(email), Some(token)) = (keyring_email, keyring_token) {
        if !email.trim().is_empty() && !token.trim().is_empty() {
            return Some((email.trim().to_string(), token.trim().to_string()));
        }
    }
    read_file_credentials()
}

pub fn set_stored(email: &str, refresh_token: &str) {
    if is_e2e_config() {
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
    let service = service_name();
    let _ = keyring::Entry::new(service, KEY_EMAIL).and_then(|e| e.delete_credential());
    let _ = keyring::Entry::new(service, KEY_REFRESH_TOKEN).and_then(|e| e.delete_credential());
    remove_file_credentials();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_store_and_get() {
        clear_stored();
        set_stored("mbrandstaetter48@gmail.com", "dummy_token_123");
        let res = get_stored();
        assert_eq!(res, Some(("mbrandstaetter48@gmail.com".to_string(), "dummy_token_123".to_string())));
        clear_stored();
        assert_eq!(get_stored(), None);
    }
}

