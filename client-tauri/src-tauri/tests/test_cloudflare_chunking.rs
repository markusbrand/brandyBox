use brandybox_lib::api::ApiClient;
use brandybox_lib::sync;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

fn compute_sha256(path: &Path) -> String {
    let mut file = File::open(path).expect("open file for hash");
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let n = file.read(&mut buffer).expect("read file");
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }
    format!("{:x}", hasher.finalize())
}

fn get_admin_client(cloudflare_url: &str) -> ApiClient {
    let output = std::process::Command::new("docker")
        .args([
            "exec",
            "brandybox-backend",
            "python",
            "-c",
            "from app.auth.jwt import create_access_token, create_refresh_token; print(f'{create_access_token(\"mbrandstaetter48@gmail.com\")}|{create_refresh_token(\"mbrandstaetter48@gmail.com\")}')",
        ])
        .output()
        .expect("failed to execute docker command");

    assert!(output.status.success(), "Failed to generate admin tokens");
    let tokens = String::from_utf8(output.stdout).expect("utf8").trim().to_string();
    let parts: Vec<&str> = tokens.split('|').collect();
    let access_token = parts[0].to_string();
    let refresh_token = parts[1].to_string();

    let mut client = ApiClient::new(cloudflare_url.to_string());
    client.set_access_token(Some(access_token));
    client.set_refresh_token(Some(refresh_token));
    client
}

fn get_user_client(cloudflare_url: &str, email: &str) -> ApiClient {
    let output = std::process::Command::new("docker")
        .args([
            "exec",
            "brandybox-backend",
            "python",
            "-c",
            &format!("from app.auth.jwt import create_access_token, create_refresh_token; print(f'{{create_access_token(\"{email}\")}}|{{create_refresh_token(\"{email}\")}}')"),
        ])
        .output()
        .expect("failed to execute docker command");

    assert!(output.status.success(), "Failed to generate user tokens");
    let tokens = String::from_utf8(output.stdout).expect("utf8").trim().to_string();
    let parts: Vec<&str> = tokens.split('|').collect();
    let access_token = parts[0].to_string();
    let refresh_token = parts[1].to_string();

    let mut client = ApiClient::new(cloudflare_url.to_string());
    client.set_access_token(Some(access_token));
    client.set_refresh_token(Some(refresh_token));
    client
}

#[test]
#[ignore = "requires live cloudflare tunnel"]
fn test_cloudflare_chunked_upload_and_download() {
    let cloudflare_url = "https://brandybox.brandstaetter.rocks";
    let admin = get_admin_client(cloudflare_url);

    let test_email = format!("test_chunk_{}@example.com", uuid::Uuid::new_v4());
    admin.create_user(&test_email, "Test", "Chunk").expect("create user");

    let client = get_user_client(cloudflare_url, &test_email);

    // 2. Create a temporary 120MB file
    let temp_dir = std::env::temp_dir().join(format!("bb_cf_test_{}", uuid::Uuid::new_v4()));
    std::fs::create_dir_all(&temp_dir).expect("create temp dir");
    let large_file_path = temp_dir.join("test_120mb_chunked.bin");

    println!("Generating 120MB test file...");
    {
        let mut f = File::create(&large_file_path).expect("create test file");
        let pattern = [0x5au8; 1024 * 1024]; // 1MB repeated pattern
        for _ in 0..120 {
            f.write_all(&pattern).expect("write 1MB block");
        }
        f.flush().expect("flush");
    }

    let orig_hash = compute_sha256(&large_file_path);
    println!("120MB test file SHA256: {}", orig_hash);

    // 3. Upload 120MB file using ApiClient (exercises upload_file_chunked with 20MB chunks)
    println!("Uploading 120MB chunked file through Cloudflare tunnel...");
    let upload_res = client.upload_file_from_path("test_120mb_chunked.bin", &large_file_path);
    assert!(upload_res.is_ok(), "Upload failed: {:?}", upload_res);
    println!("120MB chunked upload succeeded!");

    // 4. Download 120MB file back through Cloudflare tunnel
    let downloaded_path = temp_dir.join("downloaded_120mb.bin");
    println!("Downloading 120MB file through Cloudflare tunnel...");
    let dl_bytes = client
        .download_file_to_path("test_120mb_chunked.bin", &downloaded_path)
        .expect("download failed");
    assert_eq!(dl_bytes, 120 * 1024 * 1024, "Downloaded size mismatch");

    let dl_hash = compute_sha256(&downloaded_path);
    println!("Downloaded file SHA256: {}", dl_hash);
    assert_eq!(orig_hash, dl_hash, "SHA256 checksum mismatch after download");
    println!("Checksum verified: exact bit-for-bit match!");

    // 5. Cleanup
    let _ = admin.delete_user(&test_email);
    let _ = std::fs::remove_dir_all(&temp_dir);
    println!("Cleaned up test files.");
}

#[test]
#[ignore = "requires live cloudflare tunnel"]
fn test_cloudflare_sync_engine_with_chunked_files() {
    let cloudflare_url = "https://brandybox.brandstaetter.rocks";
    let admin = get_admin_client(cloudflare_url);

    let test_email = format!("test_sync_{}@example.com", uuid::Uuid::new_v4());
    admin.create_user(&test_email, "Test", "Sync").expect("create user");

    let mut client = get_user_client(cloudflare_url, &test_email);

    // Setup isolated sync directory with BRANDYBOX_CONFIG_DIR
    let test_uuid = uuid::Uuid::new_v4();
    let test_root = std::env::temp_dir().join(format!("bb_sync_test_{}", test_uuid));
    let test_config_dir = std::env::temp_dir().join(format!("bb_config_test_{}", test_uuid));
    std::fs::create_dir_all(&test_root).expect("create sync dir");
    std::fs::create_dir_all(&test_config_dir).expect("create config dir");
    std::env::set_var("BRANDYBOX_CONFIG_DIR", &test_config_dir);

    // Create 75MB test file (which triggers chunking: 4 chunks)
    let sync_file_rel = "sync_test_75mb.bin";
    let sync_file_local = test_root.join(sync_file_rel);
    println!("Creating 75MB file for sync engine test...");
    {
        let mut f = File::create(&sync_file_local).expect("create sync test file");
        let block = [0x3cu8; 1024 * 1024];
        for _ in 0..75 {
            f.write_all(&block).expect("write block");
        }
        f.flush().expect("flush");
    }

    // Run sync
    println!("Running sync engine against Cloudflare tunnel...");
    let sync_result = sync::run_sync(&mut client, &test_root);
    assert!(sync_result.is_ok(), "Sync failed: {:?}", sync_result);
    let (dl, up, warn) = sync_result.unwrap();
    println!("Sync completed: uploaded={} bytes, downloaded={} bytes, warning={:?}", up, dl, warn);
    assert_eq!(up, 75 * 1024 * 1024, "Expected exactly 75MB uploaded");
    assert_eq!(dl, 0, "Expected 0 downloaded on new clean user root");
    assert!(warn.is_none(), "Sync had warnings: {:?}", warn);

    // Cleanup
    let _ = admin.delete_user(&test_email);
    let _ = std::fs::remove_dir_all(&test_root);
    let _ = std::fs::remove_dir_all(&test_config_dir);
    println!("Sync engine chunking test finished successfully!");
}

#[test]
#[ignore = "requires live cloudflare tunnel"]
fn test_cloudflare_mixed_multi_file_two_way_sync() {
    let cloudflare_url = "https://brandybox.brandstaetter.rocks";
    let admin = get_admin_client(cloudflare_url);

    let test_email = format!("test_mixed_{}@example.com", uuid::Uuid::new_v4());
    admin.create_user(&test_email, "Test", "Mixed").expect("create user");

    let mut client_a = get_user_client(cloudflare_url, &test_email);
    let mut client_b = get_user_client(cloudflare_url, &test_email);

    // Setup Client A directory with small (2MB), medium (55MB - chunked), and large (105MB - chunked) files
    let test_uuid = uuid::Uuid::new_v4();
    let root_a = std::env::temp_dir().join(format!("bb_sync_a_{}", test_uuid));
    let config_a = std::env::temp_dir().join(format!("bb_cfg_a_{}", test_uuid));
    let root_b = std::env::temp_dir().join(format!("bb_sync_b_{}", test_uuid));
    let config_b = std::env::temp_dir().join(format!("bb_cfg_b_{}", test_uuid));

    std::fs::create_dir_all(&root_a).expect("create root_a");
    std::fs::create_dir_all(&config_a).expect("create config_a");
    std::fs::create_dir_all(&root_b).expect("create root_b");
    std::fs::create_dir_all(&config_b).expect("create config_b");

    let file_small = "folder1/small.bin";
    let file_medium = "folder1/medium.bin";
    let file_large = "folder2/large.bin";

    std::fs::create_dir_all(root_a.join("folder1")).expect("mkdir folder1");
    std::fs::create_dir_all(root_a.join("folder2")).expect("mkdir folder2");

    // Write 2MB small file
    {
        let mut f = File::create(root_a.join(file_small)).expect("create small");
        f.write_all(&vec![0x11u8; 2 * 1024 * 1024]).expect("write small");
    }
    // Write 55MB medium file (triggers 3 chunks: 20MB + 20MB + 15MB)
    {
        let mut f = File::create(root_a.join(file_medium)).expect("create medium");
        let chunk_block = vec![0x22u8; 1024 * 1024];
        for _ in 0..55 {
            f.write_all(&chunk_block).expect("write medium block");
        }
    }
    // Write 105MB large file (triggers 6 chunks: 20MB x 5 + 5MB, >100MB Cloudflare limit)
    {
        let mut f = File::create(root_a.join(file_large)).expect("create large");
        let chunk_block = vec![0x33u8; 1024 * 1024];
        for _ in 0..105 {
            f.write_all(&chunk_block).expect("write large block");
        }
    }

    let hash_small_orig = compute_sha256(&root_a.join(file_small));
    let hash_medium_orig = compute_sha256(&root_a.join(file_medium));
    let hash_large_orig = compute_sha256(&root_a.join(file_large));

    // Sync Client A -> Remote (upload small, chunked medium, chunked large)
    std::env::set_var("BRANDYBOX_CONFIG_DIR", &config_a);
    println!("Syncing Client A (uploads) to Cloudflare...");
    let res_a = sync::run_sync(&mut client_a, &root_a).expect("Sync A failed");
    println!("Sync A finished: uploaded {} bytes, downloaded {} bytes, warnings: {:?}", res_a.1, res_a.0, res_a.2);
    assert_eq!(res_a.1, (2 + 55 + 105) * 1024 * 1024);
    assert!(res_a.2.is_none());

    // Sync Client B -> Remote (downloads all 3 files from Remote)
    std::env::set_var("BRANDYBOX_CONFIG_DIR", &config_b);
    println!("Syncing Client B (downloads) from Cloudflare...");
    let res_b = sync::run_sync(&mut client_b, &root_b).expect("Sync B failed");
    println!("Sync B finished: uploaded {} bytes, downloaded {} bytes, warnings: {:?}", res_b.1, res_b.0, res_b.2);
    assert_eq!(res_b.0, (2 + 55 + 105) * 1024 * 1024);
    assert!(res_b.2.is_none());

    // Verify integrity of all files on Client B
    let hash_small_b = compute_sha256(&root_b.join(file_small));
    let hash_medium_b = compute_sha256(&root_b.join(file_medium));
    let hash_large_b = compute_sha256(&root_b.join(file_large));

    assert_eq!(hash_small_orig, hash_small_b, "Small file hash mismatch on Client B");
    assert_eq!(hash_medium_orig, hash_medium_b, "Medium file hash mismatch on Client B");
    assert_eq!(hash_large_orig, hash_large_b, "Large file hash mismatch on Client B");
    println!("All downloaded files verified bit-for-bit on Client B!");

    // Delete locally on Client A and sync to verify remote deletion
    std::env::set_var("BRANDYBOX_CONFIG_DIR", &config_a);
    std::fs::remove_file(root_a.join(file_small)).expect("rm small");
    std::fs::remove_file(root_a.join(file_medium)).expect("rm medium");
    std::fs::remove_file(root_a.join(file_large)).expect("rm large");

    println!("Syncing Client A (propagates deletions to Remote)...");
    let res_a_del = sync::run_sync(&mut client_a, &root_a).expect("Sync A delete failed");
    assert!(res_a_del.2.is_none());

    // Cleanup
    let _ = admin.delete_user(&test_email);
    let _ = std::fs::remove_dir_all(&root_a);
    let _ = std::fs::remove_dir_all(&config_a);
    let _ = std::fs::remove_dir_all(&root_b);
    let _ = std::fs::remove_dir_all(&config_b);
    println!("Multi-client two-way sync with chunking test finished successfully!");
}
