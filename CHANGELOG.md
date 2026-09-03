# Changelog

## [1.2.2](https://github.com/markusbrand/brandyBox/compare/brandybox-v1.2.1...brandybox-v1.2.2) (2026-09-03)


### Bug Fixes

* **client-tauri:** add native macOS menu bar tray, app menu, token refresh & sync resilience ([fda6539](https://github.com/markusbrand/brandyBox/commit/fda6539ae28cb197ae7ef12e5bb200760cb01903))

## [1.2.1](https://github.com/markusbrand/brandyBox/compare/brandybox-v1.2.0...brandybox-v1.2.1) (2026-09-01)


### Bug Fixes

* **client:** start app silently to tray without opening settings window ([bfa5c24](https://github.com/markusbrand/brandyBox/commit/bfa5c24f4e615d06f9d2763e05256305622a3a06))

## [1.2.0](https://github.com/markusbrand/brandyBox/compare/brandybox-v1.1.0...brandybox-v1.2.0) (2026-08-25)


### Features

* implement streaming uploads and atomic sync writes ([a665267](https://github.com/markusbrand/brandyBox/commit/a6652677583ec3058f880fa62470d3d0f5a24206))
* **ui:** add aria-label to icon buttons for accessibility ([1a5754a](https://github.com/markusbrand/brandyBox/commit/1a5754a5935641334d4033ae17939c42278620e5))
* **ux:** Add loading state to login buttons ([58c4a63](https://github.com/markusbrand/brandyBox/commit/58c4a638fded5c29416c4e783f3507dccea708b0))


### Bug Fixes

* admin promotion, consolidate Linux starters, and ensure logo consistency ([b397bbb](https://github.com/markusbrand/brandyBox/commit/b397bbbba234379c0dc97a3613a784a9818c2720))
* **ci:** resolve duplicate CircularProgress import and chunked upload UUID validation ([e941fee](https://github.com/markusbrand/brandyBox/commit/e941feebacd65897c3c358ebd1f9539d9c14289a))
* **client-tauri:** remember and restore settings window desktop position ([3d14b05](https://github.com/markusbrand/brandyBox/commit/3d14b05c08ca7b60b67d4d99748564e82cc7e4fe))
* **client-tauri:** set GDK_BACKEND=x11 on Linux for window positioning and tray support ([07ed4ca](https://github.com/markusbrand/brandyBox/commit/07ed4ca5b716cee45bd3a65f43ed64ed48305336))
* **client-tauri:** start app minimized to system tray and open window via tray menu ([9d71ec2](https://github.com/markusbrand/brandyBox/commit/9d71ec23145120948172b31ba8200749cb860159))
* fix CI errors from previous performance optimization ([254571b](https://github.com/markusbrand/brandyBox/commit/254571b0ebfe288026c4f82ddce8bc0ff294e0e2))
* resolve CI failures by reverting duplicate import and type hint issues ([e2cbf6f](https://github.com/markusbrand/brandyBox/commit/e2cbf6f74e1f439397a8142c2841e2f98a812eca))
* **security:** restrict CORS allow_headers to prevent arbitrary headers ([65f1f44](https://github.com/markusbrand/brandyBox/commit/65f1f44b7f2308cf1d16de1175e66d98f9015294))
* Store JWT tokens in sessionStorage instead of localStorage ([f319e5e](https://github.com/markusbrand/brandyBox/commit/f319e5e9dbf9cb00a8edd53f0e1ef8312767bc70))
* **web:** ensure Google sign-in button visibility based on OAuth configuration ([72a2a29](https://github.com/markusbrand/brandyBox/commit/72a2a299bcb51d805d923aef8d15927117be40ae))
* **web:** hide Google sign-in unless OAuth env is configured ([725ae23](https://github.com/markusbrand/brandyBox/commit/725ae2312ef5133023000e2caddaf58b749f0953))
* **web:** serve SPA index for client routes and mount Vite assets under /assets ([cce68af](https://github.com/markusbrand/brandyBox/commit/cce68af6c15d59849973a6e032169ca259e4c827))


### Performance Improvements

* **backend:** offload recursive file listing to thread pool\n\nSynchronous recursive file and directory listings (`os.scandir`) in `list_files_recursive` and `list_directories_recursive` were blocking the main asyncio event loop in FastAPI, causing significant latency for all concurrent users when deep directory structures were queried.\n\nThis commit wraps these calls in `anyio.to_thread.run_sync()` to safely offload the heavy disk I/O to a background thread pool, freeing up the event loop to process other API requests concurrently. ([5130ac0](https://github.com/markusbrand/brandyBox/commit/5130ac061f76876e5663fdb04c10392b1d84c9a7))
* **files:** replace pathlib.rglob with os.scandir for faster tree traversal ([5bf762c](https://github.com/markusbrand/brandyBox/commit/5bf762c88f72e31fdea942116c22937bcc363881))
* offload recursive file system traversals to worker threads ([378b621](https://github.com/markusbrand/brandyBox/commit/378b62196cd42e366a555b43f67ad85694b78dba))
* Optimize file listing and run in thread ([5e9fac9](https://github.com/markusbrand/brandyBox/commit/5e9fac9ca35f37989c662a38404c14b13b7168e3))
* Optimize file upload handlers with aiofiles ([a315170](https://github.com/markusbrand/brandyBox/commit/a315170c29ae7ea506ce61b19b4c338b0df907d6))
* optimize get_disk_usage_bytes with os.scandir and asyncio ([11a7ce6](https://github.com/markusbrand/brandyBox/commit/11a7ce63e7e8138b00fc7bd6894f286b4071a347))
* optimize get_hashes_for_paths query chunking ([94d37a5](https://github.com/markusbrand/brandyBox/commit/94d37a5ce3c50159c1ef71fa80b84f6dcc37b5b9))


### Code Refactoring

* **backend:** move hash_model registration to session.py ([a5f4434](https://github.com/markusbrand/brandyBox/commit/a5f4434e22d2367678f70b1d8594085cf2c27235))
* **tests:** decompose main function in run_autonomous_sync.py ([e5b9862](https://github.com/markusbrand/brandyBox/commit/e5b98623701d45b0a60fff3308d17ea536225475))
