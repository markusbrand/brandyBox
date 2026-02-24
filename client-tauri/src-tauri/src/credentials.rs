//! Keyring-backed credential storage (email + refresh_token). Matches Python keyring usage.

const SERVICE_NAME: &str = "BrandyBox";
const KEY_EMAIL: &str = "email";
const KEY_REFRESH_TOKEN: &str = "refresh_token";

fn service_name() -> &'static str {
    if std::env::var("BRANDYBOX_CONFIG_DIR").map(|s| !s.trim().is_empty()).unwrap_or(false) {
        "BrandyBox-E2E"
    } else {
        SERVICE_NAME
    }
}

pub fn get_stored() -> Option<(String, String)> {
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
    let service = service_name();
    let _ = keyring::Entry::new(service, KEY_EMAIL).and_then(|e| e.set_password(email));
    let _ = keyring::Entry::new(service, KEY_REFRESH_TOKEN).and_then(|e| e.set_password(refresh_token));
}

pub fn clear_stored() {
    let service = service_name();
    let _ = keyring::Entry::new(service, KEY_EMAIL).and_then(|e| e.delete_password());
    let _ = keyring::Entry::new(service, KEY_REFRESH_TOKEN).and_then(|e| e.delete_password());
}
