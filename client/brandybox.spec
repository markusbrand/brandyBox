# PyInstaller spec for Brandy Box client (one-folder build for installers).
# Run from repo root: pyinstaller client/brandybox.spec
# Output: dist/BrandyBox/ with BrandyBox executable and assets

from pathlib import Path

# Repo root (parent of client/)
repo_root = Path(SPECPATH).resolve().parent
assets_src = repo_root / "assets" / "logo"
assets_dest = "assets/logo"

a = Analysis(
    [str(repo_root / "client" / "brandybox" / "main.py")],
    pathex=[str(repo_root / "client")],
    datas=[(str(assets_src), assets_dest)] if assets_src.exists() else [],
    hiddenimports=[
        "pystray", "PIL", "PIL._tkinter_finder", "keyring", "httpx",
        "brandybox.ui", "brandybox.ui.settings", "brandybox.ui.dialogs",
        "brandybox.sync", "brandybox.sync.engine", "brandybox.sync.watcher",
        "brandybox.api", "brandybox.api.client", "brandybox.auth", "brandybox.auth.credentials",
        "brandybox.config",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BrandyBox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BrandyBox",
)
