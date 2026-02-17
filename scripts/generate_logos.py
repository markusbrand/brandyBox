#!/usr/bin/env python3
"""Generate Brandy Box tray icons (synced, syncing, error) and sizes 16/32.
Uses only stdlib (zlib, struct). Run from repo root: python scripts/generate_logos.py
If Pillow is installed, draws rounded box with 'B' so the tray icon looks distinct.
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


def _draw_tray_icon_pillow(size: int, fill_rgb: tuple, filename: str) -> None:
    """Draw a rounded box with 'B' using Pillow (tray-friendly icon)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        ASSETS.joinpath(filename).write_bytes(solid_png(size, *fill_rgb, 255))
        return
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = max(2, size // 12)
    r = margin * 2
    d.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=r,
        fill=fill_rgb + (255,),
        outline=(255, 255, 255, 180),
        width=max(1, size // 32),
    )
    # Simple "B" so the icon is recognizable
    font = None
    for path in (
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            font = ImageFont.truetype(path, max(8, size // 2))
            break
        except (OSError, TypeError):
            continue
    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
    if font:
        text = "B"
        if hasattr(d, "textbbox"):
            bbox = d.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        else:
            tw, th = d.textsize(text, font=font) if hasattr(d, "textsize") else (size // 2, size // 3)
        x = (size - tw) // 2
        y = (size - th) // 2 - (size // 16)
        d.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    img.save(ASSETS / filename, "PNG")


def main() -> None:
    # Main logo (blue) – small sizes stay solid for installer/desktop
    for size, name in [(16, "icon_16.png"), (32, "icon_32.png")]:
        ASSETS.joinpath(name).write_bytes(solid_png(size, 70, 130, 180))
    # Tray state icons: use Pillow for a proper icon if available
    _draw_tray_icon_pillow(64, (70, 130, 180), "icon_synced.png")   # steel blue
    _draw_tray_icon_pillow(64, (255, 180, 80), "icon_syncing.png")  # amber
    _draw_tray_icon_pillow(64, (220, 80, 80), "icon_error.png")     # soft red
    print("Logos written to", ASSETS)


if __name__ == "__main__":
    main()
