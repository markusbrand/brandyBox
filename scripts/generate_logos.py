#!/usr/bin/env python3
"""Generate Brandy Box application and tray icons (SVG, PNG, ICO) across all required resolutions.
Run from repo root: python scripts/generate_logos.py
"""

import subprocess
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "assets" / "logo"
TAURI_ICONS = REPO_ROOT / "client-tauri" / "src-tauri" / "icons"
ASSETS.mkdir(parents=True, exist_ok=True)
TAURI_ICONS.mkdir(parents=True, exist_ok=True)

# Exact vector path coordinates for bold centered 'B'
B_PATH_D = (
    "M 253.40 229.70 Q 267.65 229.70 274.95 223.45 Q 282.30 217.20 282.30 205.00 "
    "Q 282.30 192.95 274.95 186.65 Q 267.65 180.30 253.40 180.30 L 220.15 180.30 "
    "L 220.15 229.70 L 253.40 229.70 Z M 255.45 331.70 Q 273.55 331.70 282.70 324.05 "
    "Q 291.85 316.40 291.85 300.95 Q 291.85 285.75 282.80 278.20 Q 273.75 270.60 "
    "255.45 270.60 L 220.15 270.60 L 220.15 331.70 L 255.45 331.70 Z M 311.40 247.80 "
    "Q 330.75 253.45 341.35 268.60 Q 352.00 283.75 352.00 305.75 Q 352.00 339.50 "
    "329.20 356.10 Q 306.40 372.65 259.80 372.65 L 160.00 372.65 L 160.00 139.35 "
    "L 250.30 139.35 Q 298.90 139.35 320.70 154.05 Q 342.50 168.75 342.50 201.10 "
    "Q 342.50 218.10 334.50 230.05 Q 326.55 242.00 311.40 247.80 Z"
)


def create_svg(color_top="#1e88e5", color_bottom="#0d47a1", status_color=None) -> str:
    status_svg = ""
    if status_color:
        status_svg = f'''
  <circle cx="390" cy="390" r="56" fill="{status_color}" stroke="#ffffff" stroke-width="12"/>'''

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="brandyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{color_top}"/>
      <stop offset="100%" stop-color="{color_bottom}"/>
    </linearGradient>
    <filter id="dropShadow" x="-10%" y="-10%" width="120%" height="125%">
      <feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
  </defs>
  <rect x="44" y="44" width="424" height="424" rx="96" ry="96" fill="url(#brandyGrad)" filter="url(#dropShadow)" stroke="rgba(255,255,255,0.45)" stroke-width="8"/>
  <path d="{B_PATH_D}" fill="#ffffff"/>{status_svg}
</svg>
'''


def render_svg_to_png(svg_path: Path, png_path: Path, size: int) -> None:
    subprocess.run(
        ["rsvg-convert", "-w", str(size), "-h", str(size), str(svg_path), "-o", str(png_path)],
        check=True
    )


def main() -> None:
    print("Writing SVG logos...")
    main_svg = ASSETS / "brandybox.svg"
    syncing_svg = ASSETS / "icon_syncing.svg"
    error_svg = ASSETS / "icon_error.svg"

    main_svg.write_text(create_svg(color_top="#1e88e5", color_bottom="#0d47a1"))
    syncing_svg.write_text(create_svg(color_top="#ffa000", color_bottom="#e65100", status_color="#ffeb3b"))
    error_svg.write_text(create_svg(color_top="#e53935", color_bottom="#b71c1c", status_color="#ff5252"))

    (TAURI_ICONS / "brandybox.svg").write_text(main_svg.read_text())

    print("Rendering PNG sizes from SVG using rsvg-convert...")
    sizes = [16, 22, 24, 32, 44, 48, 64, 71, 89, 107, 128, 142, 150, 256, 284, 310, 512]
    
    for s in sizes:
        dest_png = TAURI_ICONS / f"{s}x{s}.png" if s in [32, 128] else None
        if s == 256:
            dest_png = TAURI_ICONS / "128x128@2x.png"
        elif s == 512:
            dest_png = TAURI_ICONS / "icon.png"

        if dest_png:
            render_svg_to_png(main_svg, dest_png, s)

        if s in [16, 32, 48, 64, 128, 256, 512]:
            render_svg_to_png(main_svg, ASSETS / f"icon_{s}.png", s)

        sq_map = {
            30: "Square30x30Logo.png",
            44: "Square44x44Logo.png",
            71: "Square71x71Logo.png",
            89: "Square89x89Logo.png",
            107: "Square107x107Logo.png",
            142: "Square142x142Logo.png",
            150: "Square150x150Logo.png",
            284: "Square284x284Logo.png",
            310: "Square310x310Logo.png",
        }
        if s in sq_map:
            render_svg_to_png(main_svg, TAURI_ICONS / sq_map[s], s)

    render_svg_to_png(main_svg, TAURI_ICONS / "StoreLogo.png", 50)
    render_svg_to_png(main_svg, TAURI_ICONS / "Square30x30Logo.png", 30)

    # Tray state icons (64x64)
    render_svg_to_png(main_svg, ASSETS / "icon_synced.png", 64)
    render_svg_to_png(syncing_svg, ASSETS / "icon_syncing.png", 64)
    render_svg_to_png(error_svg, ASSETS / "icon_error.png", 64)

    render_svg_to_png(main_svg, TAURI_ICONS / "icon_synced.png", 64)
    render_svg_to_png(syncing_svg, TAURI_ICONS / "icon_syncing.png", 64)
    render_svg_to_png(error_svg, TAURI_ICONS / "icon_error.png", 64)

    # Multi-size ICO for Windows
    img_512 = Image.open(TAURI_ICONS / "icon.png")
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img_512.save(TAURI_ICONS / "icon.ico", format="ICO", sizes=ico_sizes)

    print("Successfully generated all Brandy Box SVG, PNG, and ICO icons with bold 'B'.")


if __name__ == "__main__":
    main()



