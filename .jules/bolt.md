## 2024-08-19 - Replacing pathlib.rglob with os.scandir for high-performance file tree traversal
**Learning:** `pathlib.Path.rglob` is slow and memory-intensive because it yields full `Path` objects and recursively walks trees. For large, deep directories, an iterative `os.scandir` implementation with a stack handles I/O much faster and prevents stack overflow errors.
**Action:** When working on server-side functions that traverse the file system recursively, use a non-recursive `os.scandir` queue or stack. Additionally, catch `OSError` per-directory rather than on the entire traversal, so permission issues in one subdirectory don't abort the entire scan.

## 2024-05-18 - Fastapi/Asyncio filesystem traversal bottlenecks
**Learning:** Calling blocking filesystem operations like `os.scandir` recursively directly within `async def` FastAPI route handlers blocks the main asyncio event loop, causing massive concurrency issues during large directory scans (e.g. initial syncs).
**Action:** Always offload blocking I/O (like `list_files_recursive` or heavy `os.walk`) to a worker thread using `anyio.to_thread.run_sync()` in async routes.
