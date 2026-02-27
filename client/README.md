# Brandy Box Desktop Client (Python)

> **Deprecated.** This Python client is kept as fallback only. Use the **Tauri client** (`client-tauri/`) as the primary desktop app – it has a robust sync engine and works out of the box on Linux. See the root [README](../README.md).

Cross-platform desktop client for Brandy Box. Syncs a local folder to the Raspberry Pi backend.

## Development

```bash
pip install -e .
# Run from project root so assets are findable
python -m brandybox.main
```

## Building

See the root README and `assets/installers/` for PyInstaller and OS-specific installers.
