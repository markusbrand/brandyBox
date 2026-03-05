//! Keyring-backed credential storage (email + refresh_token). Matches Python keyring usage.
//! When BRANDYBOX_CONFIG_DIR is set (E2E), also supports e2e_credentials.json so CI can seed
//! credentials without a system keyring.

use crate::config;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

const SERVICE_NAME: &str = "BrandyBox";
const KEY_EMAIL: &str = "email";
const KEY_REFRESH_TOKEN: &str = "refresh_token";
const E2E_CREDENTIALS_FILENAME: &str = "e2e_credentials.json";

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

fn e2e_credentials_path() -> PathBuf {
    config::get_config_dir().join(E2E_CREDENTIALS_FILENAME)
}

#[derive(Serialize, Deserialize)]
struct E2ECredentialsFile {
    email: String,
    refresh_token: String,
}

pub fn get_stored() -> Option<(String, String)> {
    if is_e2e_config() {
        let path = e2e_credentials_path();
        if path.exists() {
            if let Ok(s) = std::fs::read_to_string(&path) {
                if let Ok(f) = serde_json::from_str::<E2ECredentialsFile>(&s) {
                    if !f.email.is_empty() && !f.refresh_token.is_empty() {
                        return Some((f.email, f.refresh_token));
                    }
                }
            }
        }
    }
    let service = service_name();
    let email = keyring::Entry::new(service, KEY_EMAIL).ok()?.get_password().ok()?;
    let token = keyring::Entry::new(service, KEY_REFRESH_TOKEN).ok()?.get_password().ok()?;
    if !email.is_empty() && !token.is_empty() {
        Some((email, token))
    } else {
        None
    }
}

pub fn set_stored(email: &str, refresh_token: &str) {
    if is_e2e_config() {
        let path = e2e_credentials_path();
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let f = E2ECredentialsFile {
            email: email.to_string(),
            refresh_token: refresh_token.to_string(),
        };
        let _ = std::fs::write(path, serde_json::to_string_pretty(&f).unwrap_or_else(|_| "{}".to_string()));
    }
    let service = service_name();
    let _ = keyring::Entry::new(service, KEY_EMAIL).and_then(|e| e.set_password(email));
    let _ = keyring::Entry::new(service, KEY_REFRESH_TOKEN).and_then(|e| e.set_password(refresh_token));
}

pub fn clear_stored() {
    if is_e2e_config() {
        let _ = std::fs::remove_file(e2e_credentials_path());
    }
    let service = service_name();
    let _ = keyring::Entry::new(service, KEY_EMAIL).and_then(|e| e.delete_password());
    let _ = keyring::Entry::new(service, KEY_REFRESH_TOKEN).and_then(|e| e.delete_password());
}
