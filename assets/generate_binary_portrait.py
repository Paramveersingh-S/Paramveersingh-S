"""Convert the profile picture into animated "binary art" (an SVG made of 0s and 1s).

Usage:  python assets/generate_binary_portrait.py [avatar.jpg] [out.svg]

The SVG is self-contained (own dark background + CSS animation), so it renders the same
on GitHub light/dark themes when embedded through an <img> tag.
"""
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/avatar.jpg")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "assets/binary-portrait.svg")

COLS = 70                  # characters per row
CELL_W, CELL_H = 3.4, 5.2  # px per character cell
FONT = 5.6                 # px
PAD = 8

random.seed(7)  # deterministic output

img = Image.open(SRC).convert("RGB")
img = ImageEnhance.Contrast(img).enhance(1.2)
img = ImageEnhance.Color(img).enhance(1.3)
ROWS = int(COLS * CELL_W / CELL_H)
small = np.asarray(img.resize((COLS, ROWS), Image.LANCZOS), dtype=float)

# edge map -> rim-lights the (almost black) samurai silhouette so it stays readable
_lum = (0.299 * small[..., 0] + 0.587 * small[..., 1] + 0.114 * small[..., 2]) / 255.0
_gy, _gx = np.gradient(_lum)
EDGE = np.hypot(_gx, _gy)
EDGE = EDGE / (np.percentile(EDGE, 99) + 1e-9)

# circular mask (the avatar is round)
yy, xx = np.mgrid[0:ROWS, 0:COLS]
cx, cy = (COLS - 1) / 2, (ROWS - 1) / 2
inside = ((xx - cx) / (COLS / 2)) ** 2 + ((yy - cy) / (ROWS / 2)) ** 2 <= 1.0

PALETTE = {
    "sun1": "#ff3b3b",  # bright red sun
    "sun2": "#b3121b",  # deep red
    "w1": "#f5f5f5",    # highlights / rim light
    "w2": "#c2c2c2",
    "w3": "#808080",
    "w4": "#5a5a5a",
    "dim": "#2a3140",   # faint background field
}


def classify(px, edge):
    r, g, b = px
    lum = 255 * ((0.299 * r + 0.587 * g + 0.114 * b) / 255) ** 0.65  # lift shadows
    if r > 110 and r > 1.6 * g and r > 1.6 * b:
        return ("sun1" if r > 180 else "sun2"), 150
    if edge > 0.55:
        return ("w1" if edge > 0.9 else "w2"), max(lum, 170)
    if lum > 205:
        return "w1", lum
    if lum > 140:
        return "w2", lum
    if lum > 80:
        return "w3", lum
    if lum > 45:
        return "w4", lum
    return "dim", 40


rows_svg = []
for y in range(ROWS):
    runs, cur_cls, buf = [], None, ""
    for x in range(COLS):
        cls, ch = None, " "
        if inside[y, x]:
            c, lum = classify(small[y, x], EDGE[y, x])
            if not (c == "dim" and random.random() < 0.45):
                cls = c
                # brighter pixels favour "1", darker favour "0" -> reads like a bitmap
                p_one = min(0.92, max(0.08, lum / 255 * 0.9 + 0.05))
                ch = "1" if random.random() < p_one else "0"
        if cls != cur_cls:
            if buf:
                runs.append((cur_cls, buf))
            buf, cur_cls = "", cls
        buf += ch
    if buf:
        runs.append((cur_cls, buf))
    parts = []
    for cls, text in runs:
        if cls is None:
            parts.append(f"<tspan>{text}</tspan>")
        elif cls.startswith("sun"):
            parts.append(f'<tspan class="{cls}">{text}</tspan>')
        elif cls.startswith("w"):
            parts.append(f'<tspan class="{cls}">{text}</tspan>')
        else:
            parts.append(f'<tspan class="{cls}">{text}</tspan>')
    rows_svg.append(
        f'<text x="{PAD}" y="{PAD + FONT + y * CELL_H:.1f}" xml:space="preserve">{"".join(parts)}</text>'
    )

W = int(PAD * 2 + COLS * CELL_W)
H = int(PAD * 2 + ROWS * CELL_H + 6)
styles = "".join(f".{k}{{fill:{v}}}" for k, v in PALETTE.items())

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Paramveer Singh - profile picture rendered as binary code">
<defs>
<radialGradient id="bg" cx="50%" cy="42%" r="75%"><stop offset="0%" stop-color="#1a0b0f"/><stop offset="100%" stop-color="#05060a"/></radialGradient>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="12"/></clipPath>
</defs>
<style>
text{{font-family:'SFMono-Regular',Consolas,'Courier New',monospace;font-size:{FONT}px;font-weight:700;white-space:pre}}
{styles}
</style>
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="url(#bg)"/>
{chr(10).join(rows_svg)}
</g>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="none" stroke="#ff3b3b" stroke-opacity=".45" stroke-width="2"/>
</svg>
"""
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB), {COLS}x{ROWS} chars, {W}x{H}px")


