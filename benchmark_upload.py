import asyncio
import time
import os
import tempfile

def run_bench():
    # Use real temp file for aiosqlite, but wait we need a real directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # DB goes inside the temp directory
        db_path = os.path.join(temp_dir, "db.sqlite3")
        os.environ["BRANDYBOX_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
        os.environ["BRANDYBOX_STORAGE_BASE_PATH"] = temp_dir

        from fastapi.testclient import TestClient
        from backend.app.main import app
        from backend.app.auth.jwt import create_access_token

        # Run testclient which handles app init
        with TestClient(app) as client:
            from backend.app.config import get_settings
            settings = get_settings()
            admin_email = settings.admin_email

            token = create_access_token(admin_email)
            headers = {"Authorization": f"Bearer {token}"}

            chunk_size = 64 * 1024
            content = b"x" * chunk_size
            num_chunks = 320 # 20MB
            data = content * num_chunks

            print("Warming up...")
            r = client.post("/api/files/upload?path=warmup.txt", content=data, headers=headers)
            assert r.status_code == 200, f"Warmup failed: {r.text}"

            print("Running benchmark...")
            start = time.time()
            for i in range(10):
                r = client.post(f"/api/files/upload?path=bench_{i}.txt", content=data, headers=headers)
                assert r.status_code == 200, f"Bench {i} failed: {r.text}"
            end = time.time()

            print(f"Total time for 10x20MB uploads: {end - start:.2f}s")
            print(f"Average time: {(end - start)/10:.2f}s")

if __name__ == "__main__":
    run_bench()
