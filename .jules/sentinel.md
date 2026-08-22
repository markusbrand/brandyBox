
## 2024-06-25 - Path Traversal in Chunked Uploads
**Vulnerability:** A critical Path Traversal vulnerability existed in the `/api/files/upload/chunk` and `/api/files/upload/finalize` routes. The `upload_id` provided by the client was used directly to construct the directory path (`user_base / ".uploads" / upload_id`) without prior validation. An attacker could use a string like `../../../etc/passwd` to write files anywhere on the backend server.
**Learning:** Even internal tracking IDs (like `upload_id` generated during `upload/init`) that are passed back from the client must be treated as untrusted user input, as a malicious client can modify them.
**Prevention:** Always strictly validate the format of identifier strings (e.g., ensuring an ID is a valid UUID via `uuid.UUID(id)`) before using them in file system path constructions.
