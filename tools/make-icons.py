#!/usr/bin/env python3
"""Build every CoreJBH install icon and the navbar mark from assets/img/favicon.svg.

The master is `assets/img/favicon.svg`, the first tesseract mark: a cyan neon
wireframe on transparency, 48 x 48 units, stroke widths 2.1 (the two hexagons)
and 1.7 (the six connectors).

Geometry is measured once from the master and hard-coded here, because the mark
is drawn, not cropped. The outer hexagon's centreline box is (6, 3) - (42, 45);
grown by half the 2.1 stroke on every side that is

    box    = (4.95, 1.95) - (43.05, 46.05)      -> extent 44.1 units
    centre = (24, 24)

Each output is framed so that box spans `content` of the canvas and its centre
falls on the canvas centre; the mark is then rasterised straight from the master
with resvg, so the strokes and the glow filter stay vector-crisp at every size
and the field is exactly #000000, not a near-black copy of it.

Outputs (assets/img/, all opaque #000000 except the navbar mark):

    icon-512.png           512   content 0.76  PWA / install icon, "any"
    icon-192.png           192   content 0.76  PWA / install icon, "any"
    icon-512-maskable.png  512   content 0.62  kept on disk but deliberately
                                              NOT listed in
                                              manifest.webmanifest: Samsung
                                              Internet draws a white square
                                              behind a "maskable" icon on its
                                              splash screen, so the manifest
                                              now offers "any" icons only
    apple-touch-icon.png   180   content 0.76  iOS home screen
    favicon-32.png          32   content 0.94  the browser tab
    tesseract-mark.png     128   content 0.92  straight-alpha RGBA, no field
                                              box; drawn at 28-32 CSS px in the
                                              navbar and footer

Usage (from the repository root):
    python3 tools/make-icons.py
    python3 tools/make-icons.py --preview DIR     # previews only, no writes

Requires: resvg-py (pip install resvg-py) and Pillow.
"""
from __future__ import annotations

import argparse
import io
import math
import os

import resvg_py
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELD = "#000000"

# centreline box of the outer hexagon, grown by half the 2.1 stroke
BOX = (6 - 1.05, 3 - 1.05, 42 + 1.05, 45 + 1.05)
CENTRE = (24.0, 24.0)
EXTENT = max(BOX[2] - BOX[0], BOX[3] - BOX[1])          # 44.1 units
OUTER_VERTICES = ((24, 3), (42, 13.5), (42, 34.5),
                  (24, 45), (6, 34.5), (6, 13.5))
HALF_STROKE = 1.05
MASKABLE_SAFE = 0.40            # Android masks an icon to a circle of 80 % diameter

# name, pixels, content share of the canvas, opaque?
ICONS = (
    ("icon-512.png", 512, 0.76, True),
    ("icon-192.png", 192, 0.76, True),
    ("icon-512-maskable.png", 512, 0.62, True),
    ("apple-touch-icon.png", 180, 0.76, True),
    ("favicon-32.png", 32, 0.94, True),
    ("tesseract-mark.png", 128, 0.92, False),
)


def body(master: str) -> str:
    """Everything inside the master's <svg> element, verbatim."""
    start = master.index("<svg")
    inner = master.index(">", start) + 1
    end = master.rindex("</svg>")
    return master[inner:end]


def compose(inner: str, size: int, content: float) -> str:
    """The master's artwork scaled to `content` of a `size` canvas, centred."""
    k = content * size / EXTENT
    tx = size / 2.0 - CENTRE[0] * k
    ty = size / 2.0 - CENTRE[1] * k
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">'
        f'<g transform="translate({tx:.4f} {ty:.4f}) scale({k:.6f})">{inner}</g>'
        f"</svg>"
    )


def render(inner: str, size: int, content: float, opaque: bool) -> Image.Image:
    png = resvg_py.svg_to_bytes(
        svg_string=compose(inner, size, content),
        width=size,
        height=size,
        background=FIELD if opaque else None,
    )
    img = Image.open(io.BytesIO(bytes(png))).convert("RGBA")
    if not opaque:
        return img
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    canvas.alpha_composite(img)
    return canvas.convert("RGB")


def check(name: str, img: Image.Image, size: int, content: float) -> list[str]:
    """Cheap invariants: a truly black field, and a maskable mark inside the safe circle."""
    problems = []
    if img.mode == "RGB":
        probes = [(0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)]
        if content < 0.8:          # the mark cannot reach an edge midpoint here
            probes += [(size // 2, 0), (size // 2, size - 1),
                       (0, size // 2), (size - 1, size // 2)]
        for x, y in probes:
            if img.getpixel((x, y)) != (0, 0, 0):
                problems.append(f"{name}: field at ({x},{y}) is {img.getpixel((x, y))}, not #000000")
    if name.endswith("-maskable.png"):
        k = content * size / EXTENT
        far = max(math.dist(CENTRE, v) + HALF_STROKE for v in OUTER_VERTICES) * k
        if far > MASKABLE_SAFE * size:
            problems.append(f"{name}: mark reaches {far / size:.3f} of the canvas, "
                            f"outside the {MASKABLE_SAFE:.2f} safe circle")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=os.path.join(ROOT, "assets", "img", "favicon.svg"))
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "img"))
    ap.add_argument("--preview", default=None,
                    help="write previews here instead of the icon files")
    args = ap.parse_args()

    if not os.path.exists(args.master):
        raise SystemExit(f"master art not found: {args.master}")
    inner = body(open(args.master, encoding="utf-8").read())

    problems: list[str] = []
    for name, size, content, opaque in ICONS:
        img = render(inner, size, content, opaque)
        where = args.preview or args.out
        os.makedirs(where, exist_ok=True)
        path = os.path.join(where, ("preview-" if args.preview else "") + name)
        if not opaque:
            img.save(path, optimize=True)
            if args.preview:      # show the navbar mark as the dark site draws it
                over = Image.new("RGBA", img.size, (3, 11, 39, 255))
                over.alpha_composite(img)
                over.convert("RGB").save(path.replace(".png", "-on-field.png"), optimize=True)
        else:
            img.save(path, optimize=True)
        problems += check(name, img, size, content)
        print(f"{name}: {size}x{size} content {content:.2f} "
              f"{'opaque #000000' if opaque else 'transparent'} "
              f"{os.path.getsize(path)} bytes")

    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
