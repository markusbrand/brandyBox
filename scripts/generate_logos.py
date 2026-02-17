#!/usr/bin/env python3
"""Generate Brandy Box tray icons (synced, syncing, error) and sizes 16/32.
Uses only stdlib (zlib, struct). Run from repo root: python scripts/generate_logos.py
Optional: if Pillow is installed, draws rounded box; else writes solid-color PNGs.
"""

import struct
import zlib
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "logo"
ASSETS.mkdir(parents=True, exist_ok=True)


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build one PNG chunk (length + type + data + crc)."""
    blob = chunk_type + data
    crc = zlib.crc32(blob) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def solid_png(size: int, r: int, g: int, b: int, a: int = 255) -> bytes:
    """Create a solid-color RGBA PNG (no PIL)."""
    width = height = size
    raw = b""
    for y in range(height):
        raw += b"\x00"
        for x in range(width):
            raw += bytes((r, g, b, a))
    compressed = zlib.compress(raw, 9)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    signature = b"\x89PNG\r\n\x1a\n"
    chunks = (
        png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )
    return signature + chunks


def main() -> None:
    # Main logo (blue)
    for size, name in [(16, "icon_16.png"), (32, "icon_32.png")]:
        ASSETS.joinpath(name).write_bytes(solid_png(size, 70, 130, 180))
    # Tray states
    ASSETS.joinpath("icon_synced.png").write_bytes(solid_png(64, 200, 230, 200))
    ASSETS.joinpath("icon_syncing.png").write_bytes(solid_png(64, 255, 230, 180))
    ASSETS.joinpath("icon_error.png").write_bytes(solid_png(64, 255, 200, 200))
    print("Logos written to", ASSETS)


if __name__ == "__main__":
    main()
