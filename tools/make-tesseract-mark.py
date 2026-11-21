#!/usr/bin/env python3
"""Render the CoreJBH mark: a two-cube isometric tesseract on #030B27.

Geometry is computed, not traced. The 16 vertices are the corners of a 4-cube,
(x, y, z, w) with every coordinate +-1. The two cubes of the mark are its
w = -1 and w = +1 cells: the outer cell at full size, the inner cell scaled by
INNER_SCALE about the shared centre. The 32 edges of the 4-cube then fall out as
12 outer-cube edges, 12 inner-cube edges and exactly 8 vertex edges joining the
two cubes - two cubes, never three nested ones.

The 3D result is projected with an orthographic camera looking very nearly down
the cube's main diagonal (1, 1, TILT). TILT is deliberately not exactly 1: an
exact isometric view down (1, 1, 1) puts the near and far corners on one pixel,
and with a concentric inner cube its own two diagonal corners as well, so the
joining edges degenerate and the drawing reads as stacked outlines instead of
two cubes. TILT keeps the view isometric to the eye while all 16 vertices land
on their own pixel and all 8 joining edges are real chords.

The inner cell is lifted INNER_LIFT along the screen-vertical, the way a far
cell sits offset from a near one at real perspective; that offset is what keeps
the 8 joining edges from lying exactly on the inner cube's own edges.

Depth is carried by light: the near (outer) cube is the brightest electric
cyan, the far (inner) cube a step quieter, the joining edges quieter still, the
inner cube's silhouette holds a faint luminous fill, and a white-cyan core
burns in its middle.

Outputs (assets/img/):
    icon-1024.png        master, opaque #030B27
    icon-512.png  icon-192.png  apple-touch-icon.png   opaque, resampled
    favicon-32.png       heavier line and tighter framing so it survives 32 px
    tesseract-mark.png   straight-alpha RGBA for the navbar and footer

Usage: python3 tools/make-tesseract-mark.py [--preview DIR]
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FIELD = (3, 11, 39)             # #030B27
MASTER = 1024                   # design resolution; every icon is resampled from it
SS = 4                          # supersample factor for line drawing
TILT = 1.10                     # z of the camera direction (exactly 1 = isometric)
INNER_SCALE = 0.44              # inner cube edge / outer cube edge
INNER_LIFT = 0.16               # inner cube offset up-screen, in outer-cube units
CONTENT = 0.64                  # mark size as a share of the canvas (maskable padding)
LINE_W = 0.038                  # line width in cube units (outer cube edge = 2.0)

GAIN = (1.00, 0.54, 0.45)       # line brightness: outer, inner, joining edges
WIDTH = (1.00, 0.82, 0.74)      # line width: outer, inner, joining edges
BLOOM = (0.22, 0.24, 0.14)      # broad, medium, tight halo weights
CORE_W = (0.26, 0.10)           # halo, hot-spot weights
CORE_SIGMA = 0.060
INNER_FILL = 0.07


def _rgb(hex_code: int) -> np.ndarray:
    return np.array([(hex_code >> 16) & 0xFF, (hex_code >> 8) & 0xFF,
                     hex_code & 0xFF], float) / 255.0


CYAN = _rgb(0x22D3FF)       # electric cyan, near cube
CYAN_DEEP = _rgb(0x0A84D8)  # broad bloom falls off blue
CORE = _rgb(0xDDFDFF)       # white-cyan core
WHITE_CYAN = _rgb(0xA8F2FF)  # line colour at the centre of the mark


def cube_edges(scale: float = INNER_SCALE) -> list[tuple[int, int, int]]:
    """(i, j, group) for the 32 edges; group 0 = near cube, 1 = far, 2 = joining."""
    verts = np.array([[x, y, z, w] for x in (-1, 1) for y in (-1, 1)
                      for z in (-1, 1) for w in (-1, 1)], float)
    edges = []
    for i in range(len(verts)):
        for j in range(i + 1, len(verts)):
            if int(np.sum(verts[i] != verts[j])) != 1:
                continue
            if verts[i, 3] != verts[j, 3]:
                edges.append((i, j, 2))
            elif verts[i, 3] > 0:
                edges.append((i, j, 1))
            else:
                edges.append((i, j, 0))
    return edges


def geometry(master: int = MASTER, content: float = CONTENT) -> tuple[np.ndarray, list, float]:
    """Projected vertex positions (px), edge list, and px-per-cube-unit."""
    raw = np.array([[x, y, z, w] for x in (-1, 1) for y in (-1, 1)
                    for z in (-1, 1) for w in (-1, 1)], float)
    far = raw[:, 3] > 0
    p = raw[:, :3] * np.where(far[:, None], INNER_SCALE, 1.0)

    # Orthographic camera along d = (1, 1, TILT).
    d = np.array([1.0, 1.0, TILT])
    d /= np.linalg.norm(d)
    right = np.cross([0.0, 0.0, 1.0], d)
    right /= np.linalg.norm(right)
    up = np.cross(d, right)
    up /= np.linalg.norm(up)

    p = p + np.where(far[:, None], up * INNER_LIFT, 0.0)
    xy = np.stack([p @ right, -(p @ up)], axis=1)

    x0, y0 = xy.min(axis=0)
    x1, y1 = xy.max(axis=0)
    span = max(x1 - x0, y1 - y0)
    k = content * master / span
    pts = np.stack([(xy[:, 0] - (x0 + x1) / 2) * k + master / 2.0,
                    (xy[:, 1] - (y0 + y1) / 2) * k + master / 2.0], axis=1)
    return pts, cube_edges(), k


def line_layers(master: int = MASTER, line_w: float = LINE_W,
                content: float = CONTENT) -> list[np.ndarray]:
    """Anti-aliased coverage per edge group, drawn supersampled then filtered."""
    pts, edges, k = geometry(master, content)
    big = master * SS
    layers = []
    for group in range(3):
        mask = Image.new("L", (big, big), 0)
        draw = ImageDraw.Draw(mask)
        width = max(1.0, line_w * WIDTH[group] * k * SS)  # cube units -> px
        r = width / 2.0
        for i, j, grp in edges:
            if grp != group:
                continue
            a, b = tuple(pts[i] * SS), tuple(pts[j] * SS)
            draw.line([a, b], fill=255, width=int(round(width)))
            for q in (a, b):  # round caps and joints
                draw.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=255)
        layers.append(np.asarray(mask.resize((master, master), Image.BOX), float) / 255.0)
    return layers


def _blur(arr: np.ndarray, sigma: float, master: int) -> np.ndarray:
    if sigma <= 0:
        return arr
    img = Image.fromarray(np.clip(arr * 255.0, 0, 255).astype(np.uint8), "L")
    return np.asarray(img.filter(ImageFilter.GaussianBlur(sigma * master)), float) / 255.0


def _inner_silhouette(master: int, content: float) -> np.ndarray:
    """Coverage of the inner cube's projected silhouette (a hexagon)."""
    pts, _, _ = geometry(master, content)
    far = [tuple(pts[i]) for i in range(16) if i % 2 == 1]  # w = +1 corners

    def half(points):
        hull = []
        for p in points:
            while len(hull) >= 2 and ((hull[-1][0] - hull[-2][0]) * (p[1] - hull[-2][1])
                                      - (hull[-1][1] - hull[-2][1]) * (p[0] - hull[-2][0])) <= 0:
                hull.pop()
            hull.append(p)
        return hull

    ordered = sorted(far)
    poly = half(ordered)[:-1] + half(ordered[::-1])[:-1]
    mask = Image.new("L", (master * 2, master * 2), 0)
    ImageDraw.Draw(mask).polygon([(x * 2, y * 2) for x, y in poly], fill=255)
    return np.asarray(mask.resize((master, master), Image.LANCZOS), float) / 255.0


def render(master: int = MASTER, line_w: float = LINE_W,
           content: float = CONTENT) -> np.ndarray:
    """Lit image as float RGB in 0..1."""
    cov = line_layers(master, line_w, content)
    total = np.clip(cov[0] + cov[1] + cov[2], 0.0, 1.0)

    yy, xx = np.mgrid[0:master, 0:master].astype(float)
    dist = np.sqrt((xx - master / 2.0) ** 2 + (yy - master / 2.0) ** 2) / master

    bloom = (_blur(total, 0.058, master)[..., None] * CYAN_DEEP * BLOOM[0]
             + _blur(total, 0.018, master)[..., None] * CYAN * BLOOM[1]
             + _blur(total, 0.005, master)[..., None] * CYAN * BLOOM[2])

    halo = np.exp(-0.5 * (dist / CORE_SIGMA) ** 2)
    hot = np.exp(-0.5 * (dist / (CORE_SIGMA * 0.50)) ** 2)
    core = (halo[..., None] * CORE * CORE_W[0]
            + hot[..., None] * np.array([1.0, 1.0, 1.0]) * CORE_W[1])

    if INNER_FILL > 0:
        fill = _inner_silhouette(master, content)
        core = core + (fill * (0.45 + 0.55 * np.exp(-0.5 * (dist / 0.15) ** 2)))[..., None] \
            * CYAN * INNER_FILL

    t = np.clip(dist / (0.26 * content), 0.0, 1.0)[..., None]
    line_rgb = WHITE_CYAN * (1 - t) + CYAN * t

    out = np.empty((master, master, 3), float)
    out[:] = np.array(FIELD, float) / 255.0
    out = out + bloom + core
    for group in range(3):
        out = out + line_rgb * (cov[group] ** 0.9)[..., None] * GAIN[group]
    return np.clip(out, 0.0, 1.0)


def to_image(rgb: np.ndarray) -> Image.Image:
    return Image.fromarray(np.round(rgb * 255.0).astype(np.uint8), "RGB")


def to_mark(rgb: np.ndarray) -> Image.Image:
    """Straight-alpha RGBA that reproduces `rgb` exactly over FIELD."""
    art = rgb * 255.0
    field = np.array(FIELD, float)
    span = 255.0 - field
    delta = art - field
    alpha = np.clip((delta / span).max(axis=2), 0.0, 1.0)
    alpha[alpha < 0.006] = 0.0
    src = np.where((alpha > 0)[..., None], field + delta / np.maximum(alpha, 1e-4)[..., None], field)
    src = np.clip(src, 0, 255)
    return Image.fromarray(np.dstack([src, alpha * 255.0]).astype(np.uint8), "RGBA")


def write_svg(path: str) -> None:
    """The same geometry as a vector favicon, weighted to read at 16-32 px."""
    master = 64
    content = 0.84
    base = 2.90                      # stroke px in the 64-unit viewBox
    pts, edges, _ = geometry(master, content)
    paths = []
    for group in range(3):
        seg = []
        for i, j, grp in edges:
            if grp != group:
                continue
            seg.append(f"M{pts[i][0]:.2f} {pts[i][1]:.2f}L{pts[j][0]:.2f} {pts[j][1]:.2f}")
        paths.append(" ".join(seg))

    navy = "#%02X%02X%02X" % FIELD
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {master} {master}" '
        f'width="{master}" height="{master}" role="img" '
        f'aria-label="CoreJBH mark: a two-cube tesseract">\n'
        '  <defs>\n'
        '    <radialGradient id="core" cx="50%" cy="50%" r="22%">\n'
        '      <stop offset="0" stop-color="#E6FEFF" stop-opacity="0.92"/>\n'
        '      <stop offset="0.55" stop-color="#8FEBFF" stop-opacity="0.34"/>\n'
        '      <stop offset="1" stop-color="#22D3FF" stop-opacity="0"/>\n'
        '    </radialGradient>\n'
        '    <filter id="bloom" x="-30%" y="-30%" width="160%" height="160%">\n'
        '      <feGaussianBlur stdDeviation="0.55" result="b"/>\n'
        '      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>\n'
        '    </filter>\n'
        '  </defs>\n'
        f'  <rect width="{master}" height="{master}" fill="{navy}"/>\n'
        f'  <circle cx="{master / 2:.2f}" cy="{master / 2:.2f}" r="{0.24 * master:.2f}" fill="url(#core)"/>\n'
        '  <g fill="none" stroke="#22D3FF" stroke-linecap="round" stroke-linejoin="round" '
        'filter="url(#bloom)">\n'
    )
    for group, opacity in enumerate((1.0, 0.62, 0.46)):
        width = base * WIDTH[group] / WIDTH[0]
        svg += (f'    <path stroke-opacity="{opacity:.2f}" stroke-width="{width:.2f}" '
                f'd="{paths[group]}"/>\n')
    svg += "  </g>\n</svg>\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", default=None)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "assets", "img"))
    args = ap.parse_args()

    rgb = render()
    icon = to_image(rgb)

    if args.preview:
        os.makedirs(args.preview, exist_ok=True)
        icon.save(os.path.join(args.preview, "preview-icon-1024.png"))
        to_mark(rgb).save(os.path.join(args.preview, "preview-mark-1024.png"))
        print("preview written to", args.preview)
        return

    out = args.out
    icon.resize((512, 512), Image.LANCZOS).save(os.path.join(out, "icon-512.png"), optimize=True)
    icon.resize((192, 192), Image.LANCZOS).save(os.path.join(out, "icon-192.png"), optimize=True)
    icon.resize((180, 180), Image.LANCZOS).save(os.path.join(out, "apple-touch-icon.png"), optimize=True)

    # A 32 px tab icon cannot carry the full wireframe: heavier lines and a
    # tighter frame keep the two cubes readable at that size.
    to_image(render(line_w=LINE_W * 3.4, content=0.86)).resize(
        (32, 32), Image.LANCZOS).save(os.path.join(out, "favicon-32.png"), optimize=True)

    # The navbar and footer show this file at 28-32 px, so it carries a heavier
    # line and a tighter frame than the app icons.
    to_mark(render(line_w=LINE_W * 2.0, content=0.80)).save(
        os.path.join(out, "tesseract-mark.png"), optimize=True)
    write_svg(os.path.join(out, "favicon.svg"))
    print("icons written to", out)


if __name__ == "__main__":
    main()
