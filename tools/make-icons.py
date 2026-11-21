#!/usr/bin/env python3
"""Build every CoreJBH icon and the navbar mark from the approved brand art.

The master is `assets/img/brand/corejbh-2cube-v2.png`: the approved two-cube
tesseract, rendered as a cyan neon wireframe on a near-#030B27 field.

The field of a rendered PNG is never exactly the site colour (here it is a
noisy #010925 -> #030B27-ish), so the art is keyed instead of pasted:

    bg    = median colour of the 4 px border
    alpha = max over channels of (pixel - bg) / (255 - bg)   clamped to 0..1

That is the straight-alpha coverage of a light-cyan drawing over a dark field,
because every channel of the line and its glow is brighter than the field. The
un-premultiplied colour is then rebuilt as

    fg = bg + (pixel - bg) / alpha

so `fg` over `bg` reproduces the source pixel exactly, and pasting the keyed
art over #030B27 with PIL's alpha compositing gives back the approved image with
the field flattened to the site colour. Alpha below 0.010 is dropped first: that
is the field's sensor noise (bounded at alpha ~0.009 by the border spread), so
dropping it leaves an exactly flat #030B27 background rather than a speckled one.

Framing is driven by one measured number: the extent of the drawn cube, taken as
the bounding box of alpha >= 0.5 (the geometry, not the halo). Each output is
scaled so that extent covers `content` of the canvas, and the mark's measured
centre is pinned to the canvas centre.

Outputs (assets/img/):

    icon-512.png           512   content 0.80, opaque #030B27
    icon-192.png           192   content 0.80, opaque
    icon-512-maskable.png  512   content 0.64, opaque: inside the 80 % safe circle
    apple-touch-icon.png   180   content 0.80, opaque
    favicon-32.png          32   content 1.00, opaque; the tab icon
    tesseract-mark.png     128   content 0.92, straight-alpha RGBA, no field box

The navbar and footer draw tesseract-mark.png at 30 CSS px, so 128 px stays sharp
at 3x while the file remains small enough to load on every page.

Usage (from the repository root):
    python3 tools/make-icons.py
    python3 tools/make-icons.py --preview DIR     # previews only, no writes
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELD = (3, 11, 39)          # #030B27, the site and manifest colour

ALPHA_FLOOR = 0.010          # field noise sits below this
EXTENT_ALPHA = 0.5           # alpha contour used to measure the drawn cube

# name, pixels, content share of the canvas, opaque?
ICONS = (
    ("icon-512.png", 512, 0.80, True),
    ("icon-192.png", 192, 0.80, True),
    ("icon-512-maskable.png", 512, 0.64, True),
    ("apple-touch-icon.png", 180, 0.80, True),
    ("favicon-32.png", 32, 1.00, True),
    ("tesseract-mark.png", 128, 0.92, False),
)


def key(source: Image.Image) -> tuple[Image.Image, float, float, float]:
    """Key the field out of `source`.

    Returns the straight-alpha RGBA mark plus (centre x, centre y, extent) of the
    drawn cube in source pixels.
    """
    rgb = np.asarray(source.convert("RGB")).astype(np.float64)
    border = np.concatenate([
        rgb[:4].reshape(-1, 3), rgb[-4:].reshape(-1, 3),
        rgb[:, :4].reshape(-1, 3), rgb[:, -4:].reshape(-1, 3),
    ])
    bg = np.median(border, axis=0)

    alpha = np.clip(((rgb - bg) / (255.0 - bg)).max(axis=2), 0.0, 1.0)
    alpha[alpha < ALPHA_FLOOR] = 0.0

    fg = bg + (rgb - bg) / np.maximum(alpha, 1e-6)[..., None]
    fg = np.clip(fg, 0.0, 255.0)
    fg[alpha == 0] = 0.0

    mark = Image.fromarray(np.dstack([fg, alpha * 255.0]).astype(np.uint8), "RGBA")

    ys, xs = np.where(alpha >= EXTENT_ALPHA)
    if not len(xs):
        raise SystemExit("source has no visible mark")
    cx = (xs.min() + xs.max() + 1) / 2.0
    cy = (ys.min() + ys.max() + 1) / 2.0
    extent = float(max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1))
    return mark, cx, cy, extent


def render(mark: Image.Image, cx: float, cy: float, extent: float,
           size: int, content: float, opaque: bool) -> Image.Image:
    """Scale the mark so the cube spans `content` of a `size` canvas."""
    k = content * size / extent
    scaled = mark.resize((max(1, round(mark.width * k)), max(1, round(mark.height * k))),
                         Image.LANCZOS)
    offset = (round(size / 2.0 - cx * k), round(size / 2.0 - cy * k))
    if opaque:
        canvas = Image.new("RGBA", (size, size), FIELD + (255,))
        canvas.alpha_composite(scaled, offset)
        return canvas.convert("RGB")
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(scaled, offset)
    return canvas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.path.join(
        ROOT, "assets", "img", "brand", "corejbh-2cube-v2.png"))
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "img"))
    ap.add_argument("--preview", default=None,
                    help="write previews here instead of the icon files")
    args = ap.parse_args()

    if not os.path.exists(args.source):
        raise SystemExit(f"source art not found: {args.source}")
    mark, cx, cy, extent = key(Image.open(args.source))

    if args.preview:
        os.makedirs(args.preview, exist_ok=True)
        for name, size, content, opaque in ICONS:
            img = render(mark, cx, cy, extent, size, content, opaque)
            img.save(os.path.join(args.preview, "preview-" + name))
            if not opaque:  # also show what the transparent mark looks like on the site
                over = Image.new("RGBA", img.size, FIELD + (255,))
                over.alpha_composite(img)
                over.convert("RGB").save(
                    os.path.join(args.preview, "preview-" + name.replace(".png", "-on-field.png")))
        print("previews written to", args.preview)
        return

    for name, size, content, opaque in ICONS:
        img = render(mark, cx, cy, extent, size, content, opaque)
        img.save(os.path.join(args.out, name), optimize=True)
        print(f"{name}: {size}x{size} content {content:.2f} "
              f"{'opaque' if opaque else 'transparent'} "
              f"{os.path.getsize(os.path.join(args.out, name))} bytes")


if __name__ == "__main__":
    main()
