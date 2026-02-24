//! Resolve backend base URL: LAN vs Cloudflare (matches Python client logic).

const LAN_HOST: &str = "192.168.0.150";
#[allow(dead_code)]
const LAN_NETWORK_NAME: &str = "brandstaetter";
const BACKEND_PORT: &str = "8081";
const CLOUDFLARE_URL: &str = "https://brandybox.brandstaetter.rocks";

fn is_local_network() -> bool {
    if let Ok(override_url) = std::env::var("BRANDYBOX_BASE_URL") {
        if !override_url.trim().is_empty() {
            return false; // caller will use override
        }
    }
    // Try LAN reachability (short timeout)
    let url = format!("http://{}:{}/api/users/me", LAN_HOST, BACKEND_PORT);
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build();
    if let Ok(c) = client {
        if let Ok(r) = c.get(&url).send() {
            if r.status().as_u16() == 200 || r.status().as_u16() == 401 {
                return true;
            }
        }
    }
    false
}

pub fn get_base_url() -> String {
    if let Ok(override_url) = std::env::var("BRANDYBOX_BASE_URL") {
        let s = override_url.trim();
        if !s.is_empty() {
            return s.trim_end_matches('/').to_string();
        }
    }
    let mode = crate::config::get_base_url_mode();
    if mode == "manual" {
        return crate::config::get_manual_base_url().trim_end_matches('/').to_string();
    }
    if is_local_network() {
        format!("http://{}:{}", LAN_HOST, BACKEND_PORT)
    } else {
        CLOUDFLARE_URL.to_string()
    }
}
