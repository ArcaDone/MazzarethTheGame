"""Seamless PBR textures of Palazzo Bartoli's interiors, rebuilt from the user's photos of the rooms.

python m80_bartoli_texture.py  ->  Textures/Bartoli/Interni/T_PB_<name>_{D.jpg,N.png,ORM.png}

Floors (as in the photos):
  Scacchiera      white Carrara and grey bardiglio squares laid on the diagonal (hall with the chandelier)
  CementinaRosa   cement tiles: cream quatrefoil with a dusty-rose rosette on speckled grey (blue room)
  CementinaOcra   cement tiles: ochre ground with a grey-blue diamond and a four-leaf flower (study)
  CementinaPunti  beige cement tiles with four black dots (reading room), border strip FasciaCementina
  PietraGrigia    taupe-grey veined stone slabs (corridor; laid on the diagonal by rotating the UVs)
  MarmoNero       black marble for the bands around the floors and the skirting
Walls: lime paint on plaster (Intonaco) in the 1980s colours of the rooms: Bianco, Blu, Azzurro, Menta.
The modern murals of the photos (stripes, blue waves) are left out: they are not of the 1980s.

Every texture tiles: noise is made periodic in the Fourier domain and the patterns repeat on the texture
size. Each map covers a real size (SIZE_M) so the materials use world-scale UVs.
Normal maps are OpenGL (Y+), as Blender wants; in Unreal tick "Flip Green Channel" on import.
ORM = R ambient occlusion, G roughness, B metallic (0).
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "Textures", "Bartoli", "Interni")
N = 2048
# Real size covered by each texture (metres), for the UV scale of the materials.
SIZE_M = {"Scacchiera": 0.33 * 2 ** 0.5 * 2, "CementinaRosa": 0.8, "CementinaOcra": 0.8, "CementinaPunti": 0.8,
          "FasciaCementina": 0.8, "PietraGrigia": 1.6, "MarmoNero": 1.0, "Intonaco": 2.0}


def srgb_to_lin(c):
    c = np.asarray(c, np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def pnoise(n, size_px, seed, aniso=(1.0, 1.0)):
    """Periodic smooth noise in 0..1: white noise low-passed in the Fourier domain."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((n, n))
    f = np.fft.fftfreq(n)
    fy, fx = np.meshgrid(f, f, indexing="ij")
    sigma = 1.0 / max(size_px, 1e-3)
    g = np.exp(-((fx * aniso[0]) ** 2 + (fy * aniso[1]) ** 2) / (2 * sigma ** 2))
    r = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
    r -= r.min()
    return r / max(r.max(), 1e-9)


def fbm(n, size_px, seed, octaves=4, aniso=(1.0, 1.0)):
    out, amp, tot = np.zeros((n, n)), 1.0, 0.0
    for o in range(octaves):
        out += amp * pnoise(n, size_px / 2 ** o, seed + o * 17, aniso)
        tot += amp
        amp *= 0.5
    return out / tot


def blur(a, px):
    f = np.fft.fftfreq(a.shape[0])
    fy, fx = np.meshgrid(f, f, indexing="ij")
    g = np.exp(-(fx ** 2 + fy ** 2) * (2 * np.pi * px) ** 2 / 2)
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def grid(n):
    """Pixel centres in 0..1 over the texture."""
    t = (np.arange(n) + 0.5) / n
    v, u = np.meshgrid(t, t, indexing="ij")
    return u, v


def tiles(u, v, count, diagonal=False):
    """Tile index and local coords (0..1) of a square tiling; diagonal = tiles turned 45 degrees,
    'count' diamonds across the texture (the texture then holds 2*count^2 tiles)."""
    if diagonal:
        a, b = (u + v) * count, (v - u) * count
    else:
        a, b = u * count, v * count
    ia, ib = np.floor(a), np.floor(b)
    return ia, ib, a - ia, b - ib


def tile_hash(ia, ib, seed, period):
    ia, ib = np.mod(ia, period), np.mod(ib, period)
    h = np.sin(ia * 127.1 + ib * 311.7 + seed * 74.7) * 43758.5453
    return h - np.floor(h)


def grout(x, y, width):
    """1 in the joint between tiles, 0 on the tile; x, y local 0..1."""
    d = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    return np.clip(1 - d / width, 0, 1) ** 3, d


def lines(n, scale_px, seed, width_px=1.2, jitter=0.015):
    """Thin, long, wandering lines (cracks, veins): the 0.5 contour of a smooth periodic noise, with a
    width that does not depend on the slope of the noise."""
    f = pnoise(n, scale_px, seed) + jitter * (pnoise(n, 6, seed + 1) - 0.5)
    gy, gx = np.gradient(f)
    g = np.hypot(gx, gy) + 1e-9
    return np.clip(1 - np.abs(f - 0.5) / (g * width_px), 0, 1)


def marble(u, v, base, vein, seed, freq=(3, 2), turb=1.0, width=0.012, scale_px=420):
    """Periodic marble: thin veins on sine bands warped by a smooth fbm (freq are integers, so it tiles),
    with soft clouds along the veins and a net of fine secondary veins that fade in and out."""
    t = fbm(N, scale_px, seed, 4)
    phase = 2 * np.pi * (freq[0] * u + freq[1] * v) + turb * 2 * np.pi * t
    fade = np.clip(fbm(N, 260, seed + 3, 3) * 2.2 - 0.55, 0, 1)
    primary = np.exp(-(np.sin(phase) ** 2) / width) * (0.35 + 0.65 * fade)
    cloud = np.exp(-(np.sin(phase + 0.35) ** 2) / 0.35) * 0.35
    fine = blur(lines(N, 150, seed + 7, 0.9), 1.0) * np.clip(fbm(N, 200, seed + 8, 2) * 2 - 0.8, 0, 1) * 0.3
    veins = np.clip(primary + fine, 0, 1)
    mix = np.clip(veins + cloud * 0.5, 0, 1)
    col = base[None, None, :] * (0.94 + 0.08 * fbm(N, 120, seed + 9, 3))[..., None]
    return col * (1 - mix[..., None]) + vein[None, None, :] * mix[..., None], veins


def speckle(base, dark, light, seed, density=0.12):
    """Terrazzo/cement speckle: small grains of two colours over a mottled base."""
    g = pnoise(N, 1.4, seed)
    g2 = pnoise(N, 1.8, seed + 1)
    col = base[None, None, :] * (0.9 + 0.18 * fbm(N, 60, seed + 2, 3))[..., None]
    m1 = (g > 1 - density * 0.5)[..., None]
    m2 = (g2 < density * 0.4)[..., None]
    col = np.where(m1, dark, col)
    return np.where(m2, light, col)


def wear(col, height, rough, u, v, ia, ib, gr, seed, period, cracks=0.25, stain=0.25):
    """Lived-in floor: per-tile tone and lippage, dirty joints, chipped edges, a few cracks, stains."""
    h = tile_hash(ia, ib, seed, period)
    col = col * (0.93 + 0.12 * h)[..., None]
    tilt = (tile_hash(ia, ib, seed + 3, period) - 0.5) * 0.25
    height = height + tilt * 0.4
    dirt = (0.5 + 0.5 * fbm(N, 120, seed + 11, 3))
    col = col * (1 - stain * 0.35 * np.clip(dirt - 0.55, 0, 1)[..., None] * 2)
    # Joints: dark and dusty, below the tile surface.
    col = col * (1 - 0.55 * gr[..., None]) + np.array([0.10, 0.09, 0.08]) * 0.55 * gr[..., None]
    height = height - 0.9 * gr
    rough = np.maximum(rough, gr * 0.95)
    # Cracks through some tiles.
    cr_on = tile_hash(ia, ib, seed + 7, period) < cracks
    crack = lines(N, 380, seed + 13, 1.1, 0.03) * cr_on
    col = col * (1 - 0.6 * crack[..., None])
    height = height - 0.7 * crack
    rough = np.maximum(rough, crack * 0.95)
    # Worn polish: scuffs where people walk.
    scuff = fbm(N, 300, seed + 21, 2)
    rough = np.clip(rough + 0.12 * (scuff - 0.5), 0.05, 1)
    return col, height, rough


def save(name, col_lin, height, rough, strength=6.0, size=None):
    os.makedirs(OUT, exist_ok=True)

    def out(arr, fname, **kw):
        im = Image.fromarray(arr)
        if size:
            im = im.resize(size, Image.LANCZOS)
        im.save(os.path.join(OUT, fname), **kw)

    rgb = (lin_to_srgb(col_lin) * 255 + 0.5).astype(np.uint8)
    out(rgb, "T_PB_%s_D.jpg" % name, quality=92)
    if height is not None:
        dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
        dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
        # Image rows go down while V goes up: OpenGL green = +dh/dv = -dh/drow.
        nrm = np.stack([-dx, dy, np.ones_like(dx)], -1)
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
        out(((nrm * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8), "T_PB_%s_N.png" % name)
        ao = np.clip(1 - 2.5 * np.clip(blur(height, 6) - height, 0, None), 0.3, 1)
        orm = np.stack([ao, np.clip(rough, 0, 1), np.zeros_like(ao)], -1)
        out((orm * 255 + 0.5).astype(np.uint8), "T_PB_%s_ORM.png" % name)
    print("ok", name)


# ---------------------------------------------------------------------------------------------
# Floors

def scacchiera():
    """Diagonal checkerboard of white Carrara and grey bardiglio, 33 cm squares."""
    u, v = grid(N)
    count = 2
    ia, ib, x, y = tiles(u, v, count, diagonal=True)
    white, wv = marble(u, v, srgb_to_lin([226, 224, 218]), srgb_to_lin([150, 150, 152]), 3, (2, 3), 1.1, 0.010)
    grey, gv = marble(u, v, srgb_to_lin([118, 116, 112]), srgb_to_lin([78, 78, 80]), 8, (3, -2), 0.9, 0.03)
    dark = (np.mod(ia + ib, 2) == 1)[..., None]
    col = np.where(dark, grey, white)
    gr, _ = grout(x, y, 0.006)
    height = np.zeros((N, N))
    rough = np.where(dark[..., 0], 0.32, 0.26) + 0.1 * np.where(dark[..., 0], gv, wv)
    col, height, rough = wear(col, height, rough, u, v, ia, ib, gr, 31, count, cracks=0.15, stain=0.2)
    save("Scacchiera", col, height, rough, 4.0)


def cementina_rosa():
    """Cement tiles of the blue room: cream quatrefoil, dusty-rose rosette with a dark eye, grey ground."""
    u, v = grid(N)
    count = 4
    ia, ib, x, y = tiles(u, v, count)
    col = speckle(srgb_to_lin([118, 120, 118]), srgb_to_lin([45, 45, 48]), srgb_to_lin([190, 188, 182]), 41, 0.18)
    dx, dy = x - 0.5, y - 0.5
    lobes = np.zeros_like(x, bool)
    for cx, cy in ((0.25, 0), (-0.25, 0), (0, 0.25), (0, -0.25)):
        lobes |= (dx - cx) ** 2 + (dy - cy) ** 2 < 0.205 ** 2
    lobes |= dx ** 2 + dy ** 2 < 0.25 ** 2
    cream = srgb_to_lin([214, 204, 182]) * (0.94 + 0.1 * fbm(N, 40, 44, 3))[..., None]
    col = np.where(lobes[..., None], cream, col)
    r, th = np.hypot(dx, dy), np.arctan2(dy, dx)
    petal = r < 0.17 * (0.72 + 0.28 * np.abs(np.cos(4 * th)))
    col = np.where(petal[..., None], srgb_to_lin([150, 72, 82]) * (0.9 + 0.15 * fbm(N, 30, 45, 2))[..., None], col)
    col = np.where((r < 0.055)[..., None], srgb_to_lin([70, 68, 70]), col)
    gr, _ = grout(x, y, 0.008)
    height = 0.05 * fbm(N, 20, 46, 3)
    rough = 0.55 + 0.15 * fbm(N, 50, 47, 3)
    col, height, rough = wear(col, height, rough, u, v, ia, ib, gr, 48, count, cracks=0.35, stain=0.35)
    save("CementinaRosa", col, height, rough, 5.0)


def cementina_ocra():
    """Ochre cement tiles with a grey-blue diamond and a four-leaf flower in a charcoal field."""
    u, v = grid(N)
    count = 4
    ia, ib, x, y = tiles(u, v, count)
    col = speckle(srgb_to_lin([196, 162, 92]), srgb_to_lin([120, 95, 50]), srgb_to_lin([225, 205, 150]), 51, 0.22)
    dx, dy = x - 0.5, y - 0.5
    dia = np.abs(dx) + np.abs(dy)
    rim = dia < 0.46
    field = dia < 0.40
    col = np.where(rim[..., None], srgb_to_lin([128, 138, 150]), col)
    col = np.where(field[..., None], srgb_to_lin([42, 44, 50]), col)
    r, th = np.hypot(dx, dy), np.arctan2(dy, dx)
    leaf_r = 0.30 * np.abs(np.cos(2 * th)) ** 0.6
    leaf = r < leaf_r
    edge = leaf & (r > leaf_r - 0.025)
    col = np.where(leaf[..., None], srgb_to_lin([150, 160, 172]), col)
    col = np.where(edge[..., None], srgb_to_lin([60, 64, 72]), col)
    col = np.where((r < 0.04)[..., None], srgb_to_lin([42, 44, 50]), col)
    gr, _ = grout(x, y, 0.008)
    height = 0.05 * fbm(N, 20, 52, 3)
    rough = 0.55 + 0.15 * fbm(N, 50, 53, 3)
    col, height, rough = wear(col, height, rough, u, v, ia, ib, gr, 54, count, cracks=0.25, stain=0.3)
    save("CementinaOcra", col, height, rough, 5.0)


def cementina_punti():
    """Beige cement tiles with a cluster of four black squares."""
    u, v = grid(N)
    count = 4
    ia, ib, x, y = tiles(u, v, count)
    col = speckle(srgb_to_lin([186, 170, 146]), srgb_to_lin([130, 118, 100]), srgb_to_lin([210, 198, 178]), 61, 0.12)
    col = col * (0.9 + 0.2 * fbm(N, 140, 62, 3))[..., None]
    dot = np.zeros_like(x, bool)
    for cx in (-0.075, 0.075):
        for cy in (-0.075, 0.075):
            dot |= (np.abs(x - 0.5 - cx) < 0.04) & (np.abs(y - 0.5 - cy) < 0.04)
    col = np.where(dot[..., None], srgb_to_lin([30, 28, 26]), col)
    gr, _ = grout(x, y, 0.007)
    height = 0.05 * fbm(N, 20, 63, 3)
    rough = 0.6 + 0.12 * fbm(N, 50, 64, 3)
    col, height, rough = wear(col, height, rough, u, v, ia, ib, gr, 65, count, cracks=0.2, stain=0.35)
    save("CementinaPunti", col, height, rough, 5.0)


def fascia_cementina():
    """Border strip of cement tiles: charcoal ground, cream palmettes in a ring, half-moons on the edges.
    One row of four tiles runs along U; the strip is one tile (20 cm) wide (V 0..1 = one tile)."""
    u, v = grid(N)
    count = 4
    ia = np.floor(u * count)
    x, y = u * count - ia, v
    ib = np.zeros_like(ia)
    col = speckle(srgb_to_lin([46, 46, 44]), srgb_to_lin([25, 25, 25]), srgb_to_lin([90, 88, 82]), 71, 0.1)
    cream = srgb_to_lin([212, 202, 178])
    dx, dy = x - 0.5, y - 0.5
    r, th = np.hypot(dx, dy), np.arctan2(dy, dx)
    ring = np.abs(r - 0.33) < 0.035
    pet = (r < 0.27 * (0.55 + 0.45 * np.abs(np.cos(3 * th)))) & (r > 0.07)
    half = np.zeros_like(x, bool)
    for cx in (0.0, 1.0):
        half |= (x - cx) ** 2 + (y - 0.5) ** 2 < 0.13 ** 2
    for m in (ring, pet, half, np.abs(y - 0.5) > 0.46):
        col = np.where(m[..., None], cream * (0.92 + 0.1 * fbm(N, 40, 72, 2))[..., None], col)
    gr, _ = grout(x, y, 0.008)
    height = 0.05 * fbm(N, 20, 73, 3)
    rough = 0.58 + 0.12 * fbm(N, 50, 74, 3)
    col, height, rough = wear(col, height, rough, u, v, ia, ib, gr, 75, count, cracks=0.25, stain=0.3)
    save("FasciaCementina", col, height, rough, 5.0, size=(2048, 512))


def pietra_grigia():
    """Taupe-grey veined stone, 40 cm squares (vein-cut, the streaks turn from slab to slab)."""
    u, v = grid(N)
    count = 4
    ia, ib, x, y = tiles(u, v, count)
    base = srgb_to_lin([148, 137, 130])
    # Vein-cut stone: long soft streaks (anisotropic noise), across U in half the slabs and V in the rest.
    a = base[None, None, :] * (0.82 + 0.3 * fbm(N, 60, 81, 4, aniso=(1.0, 14.0)))[..., None]
    b = base[None, None, :] * (0.82 + 0.3 * fbm(N, 60, 82, 4, aniso=(14.0, 1.0)))[..., None]
    turn = (tile_hash(ia, ib, 83, count) > 0.5)[..., None]
    col = np.where(turn, a, b)
    gr, _ = grout(x, y, 0.004)
    height = np.zeros((N, N))
    rough = 0.38 + 0.1 * fbm(N, 80, 84, 3)
    col, height, rough = wear(col, height, rough, u, v, ia, ib, gr, 85, count, cracks=0.12, stain=0.2)
    save("PietraGrigia", col, height, rough, 4.0)


def marmo_nero():
    u, v = grid(N)
    col, veins = marble(u, v, srgb_to_lin([28, 28, 30]), srgb_to_lin([110, 110, 112]), 91, (2, 1), 1.2, 0.006)
    height = 0.02 * fbm(N, 30, 92, 3)
    rough = 0.22 + 0.15 * fbm(N, 200, 93, 2)
    save("MarmoNero", col, height, rough, 3.0)


# ---------------------------------------------------------------------------------------------
# Walls

WALL_COLOURS = {"Bianco": [228, 224, 214], "Blu": [52, 70, 88], "Azzurro": [104, 132, 162], "Menta": [196, 214, 196]}


def intonaco():
    """Lime paint on plaster: brushy mottling, a few hairline cracks, faint grime low down is left to the
    material (the texture tiles vertically). One shared normal/ORM, one albedo per colour."""
    u, v = grid(N)
    mott = fbm(N, 220, 101, 5)
    brush = fbm(N, 14, 102, 3, aniso=(1.0, 6.0))
    crack = lines(N, 500, 103, 0.9, 0.04) * np.clip(fbm(N, 500, 104, 2) * 3 - 1.7, 0, 1)
    height = 0.6 * mott + 0.25 * brush + 0.15 * fbm(N, 3, 105, 2)
    height = height - 0.6 * crack
    rough = 0.85 + 0.1 * fbm(N, 60, 106, 2)
    for name, rgb in WALL_COLOURS.items():
        base = srgb_to_lin(rgb)
        col = base[None, None, :] * (0.9 + 0.16 * mott + 0.05 * brush)[..., None]
        col = col * (1 - 0.45 * crack[..., None])
        save("Intonaco%s" % name, col, height if name == "Bianco" else None, rough, 2.0)
    # Shared maps under the generic name.
    for sfx in ("N.png", "ORM.png"):
        src = os.path.join(OUT, "T_PB_IntonacoBianco_" + sfx)
        dst = os.path.join(OUT, "T_PB_Intonaco_" + sfx)
        os.replace(src, dst)


def main():
    for fn in (scacchiera, cementina_rosa, cementina_ocra, cementina_punti, fascia_cementina, pietra_grigia, marmo_nero, intonaco):
        fn()


if __name__ == "__main__":
    main()
