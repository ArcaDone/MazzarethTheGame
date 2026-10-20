"""Seamless PBR textures of the stairs kit, rebuilt from photos of Mazzarino's steps and lanes.

python Scripts/m80_stairs_textures.py  ->  Saved/Mazzarino80/Stairs/Textures/T_M80_<name>_{D,N,ORM}.png
then Scripts/m80_stairs_setup.py imports them into /Game/Mazzarino80/Kit/Stairs.

  PietraLavica  dark grey basalt of the step edges, risers and copings: bush-hammered, with vesicles
  Basolato      small lava setts in rows across the stair, pale mortar joints (treads, cordonate)
  MuroConci     golden calcarenite blocks in courses, recessed mortar (walls)
  PietraSecco   pale limestone dry-stone wall, irregular rounded stones, dark gaps (country walls)
  Cemento       grey concrete render with stains (walls, treads)
  Legno         weathered wood grain along U (fence posts and rails)
  LastreBianche white limestone slabs of the panelled roads (Strada, "Pietra bianca e lavica")
  CubettiLavici small speckled lava setts of the bands between the white panels
Sizes (metres per repeat) are in SIZE_M; the meshes have UVs of one unit per metre.
Normal maps are OpenGL (Y+): the import flips the green channel for Unreal.
ORM = R ambient occlusion, G roughness, B metallic (0).
"""
import os
import random
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "Research", "Mazzarino80", "Blender"))
from m80_bartoli_texture import blur, fbm, grid, lin_to_srgb, pnoise, srgb_to_lin  # noqa: E402

OUT = os.path.join(ROOT, "Saved", "Mazzarino80", "Stairs", "Textures")
N = 2048
SIZE_M = {"PietraLavica": 1.0, "Basolato": 1.2, "MuroConci": 2.0, "PietraSecco": 2.0, "Cemento": 2.0, "Legno": 1.0}


def save(name, col_lin, height, rough, strength):
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray((lin_to_srgb(col_lin) * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, "T_M80_%s_D.png" % name))
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
    nrm = np.stack([-dx, dy, np.ones_like(dx)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    Image.fromarray(((nrm * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, "T_M80_%s_N.png" % name))
    ao = np.clip(1 - 3.0 * np.clip(blur(height, 8) - height, 0, None), 0.25, 1)
    orm = np.stack([ao, np.clip(rough, 0, 1), np.zeros_like(ao)], -1)
    Image.fromarray((orm * 255 + 0.5).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(os.path.join(OUT, "T_M80_%s_ORM.png" % name))
    print("ok", name)


def courses(rows, size_m, length_range, seed):
    """Running courses that tile: row heights (sum = 1) and, per row, block cuts along U (0..1).
    Returns per-pixel (row index, block id, distance to the nearest joint in metres, local u, local v)."""
    rnd = random.Random(seed)
    u, v = grid(N)
    hs = np.array(rows, float)
    hs /= hs.sum()
    edges = np.concatenate([[0], np.cumsum(hs)])
    row = np.clip(np.searchsorted(edges, v, side="right") - 1, 0, len(hs) - 1)
    lv = (v - edges[row]) / hs[row]
    block = np.zeros_like(u, dtype=np.int64)
    du = np.zeros_like(u)
    lu = np.zeros_like(u)
    for r in range(len(hs)):
        cuts, x = [0.0], 0.0
        while True:
            x += rnd.uniform(*length_range) / size_m
            if x > 1 - length_range[0] / size_m * 0.6:
                break
            cuts.append(x)
        cuts = np.array(cuts) + rnd.random()                 # a shift per row: joints never line up
        cuts = np.sort(np.mod(cuts, 1.0))
        cuts = np.concatenate([cuts, [cuts[0] + 1.0]])
        m = row == r
        uu = u[m] + (u[m] < cuts[0])
        k = np.searchsorted(cuts, uu, side="right") - 1
        a, b = cuts[k], cuts[k + 1]
        block[m] = r * 1000 + k
        du[m] = np.minimum(uu - a, b - uu) * size_m
        lu[m] = (uu - a) / (b - a)
    dv = np.minimum(lv, 1 - lv) * hs[row] * size_m
    return row, block, np.minimum(du, dv), lu, lv


def block_rand(block, seed):
    h = np.sin(block * 12.9898 + seed * 78.233) * 43758.5453
    return h - np.floor(h)


def pietra_lavica():
    u, v = grid(N)
    base = srgb_to_lin([74, 76, 80])
    tone = 0.85 + 0.25 * fbm(N, 260, 1, 4)
    col = base[None, None, :] * tone[..., None]
    # Weathered lighter patches and dust.
    dust = np.clip(fbm(N, 180, 2, 4) * 2.4 - 1.2, 0, 1)
    col = col * (1 - 0.5 * dust[..., None]) + srgb_to_lin([128, 124, 116]) * 0.5 * dust[..., None]
    # Vesicles: small dark pits; bush-hammered grain.
    ves = pnoise(N, 1.6, 3)
    pits = np.clip((ves - 0.80) * 8, 0, 1)
    grain = fbm(N, 2.5, 4, 2)
    col = col * (1 - 0.6 * pits[..., None]) * (0.9 + 0.2 * grain[..., None])
    # Block joints every 50 cm along U.
    ju = np.minimum(np.mod(u * 2, 1.0), 1 - np.mod(u * 2, 1.0)) * 0.5
    joint = np.clip(1 - ju / 0.004, 0, 1)
    col = col * (1 - 0.5 * joint[..., None])
    height = 0.35 * grain - 0.8 * pits + 0.3 * fbm(N, 120, 5, 3) - 1.2 * joint
    rough = 0.72 + 0.12 * grain - 0.15 * (1 - dust) * fbm(N, 300, 6, 2)
    save("PietraLavica", col, height, rough, 5.0)


def basolato():
    rows = [1.0] * 10                                        # 12 cm rows over 1.2 m
    _, block, dj, lu, lv = courses(rows, 1.2, (0.14, 0.24), 11)
    r = block_rand(block, 3)
    stone = srgb_to_lin([96, 100, 108])
    light = srgb_to_lin([138, 138, 136])
    col = stone[None, None, :] * (1 - r[..., None] * 0.6) + light * (r[..., None] * 0.6)
    col = col * (0.85 + 0.22 * fbm(N, 30, 12, 3))[..., None]
    grain = fbm(N, 2.0, 13, 2)
    col = col * (0.9 + 0.18 * grain[..., None])
    joint_w = 0.008 + 0.006 * fbm(N, 40, 14, 2)
    mortar = np.clip(1 - (dj - joint_w) / 0.006, 0, 1)
    mcol = srgb_to_lin([170, 160, 142]) * (0.8 + 0.3 * fbm(N, 25, 15, 3))[..., None]
    col = col * (1 - mortar[..., None]) + mcol * mortar[..., None]
    # Domed, worn stones; joints below.
    dome = np.clip(dj / 0.03, 0, 1) ** 0.6
    height = 0.6 * dome + 0.15 * grain + 0.1 * r - 0.8 * mortar
    rough = 0.55 + 0.2 * grain + 0.3 * mortar - 0.1 * dome
    save("Basolato", col, height, rough, 6.0)


def muro_conci():
    rnd = random.Random(21)
    rows = [rnd.uniform(0.18, 0.30) for _ in range(8)]
    _, block, dj, lu, lv = courses(rows, 2.0, (0.25, 0.55), 22)
    r = block_rand(block, 5)
    r2 = block_rand(block, 9)
    ochre = srgb_to_lin([182, 152, 104])
    grey = srgb_to_lin([150, 138, 116])
    col = ochre[None, None, :] * (1 - 0.5 * r2[..., None]) + grey * (0.5 * r2[..., None])
    col = col * (0.8 + 0.3 * r[..., None]) * (0.85 + 0.25 * fbm(N, 60, 23, 4))[..., None]
    # Eroded edges: the joint follows a noisy line, so blocks are not perfect rectangles.
    erode = dj - 0.012 * fbm(N, 25, 24, 3)
    mortar = np.clip(1 - (erode - 0.012) / 0.008, 0, 1)
    mcol = srgb_to_lin([160, 150, 130]) * (0.75 + 0.3 * fbm(N, 20, 25, 3))[..., None]
    col = col * (1 - mortar[..., None]) + mcol * mortar[..., None]
    pits = np.clip((pnoise(N, 3, 26) - 0.78) * 6, 0, 1)
    col = col * (1 - 0.35 * pits[..., None])
    face = np.clip(erode / 0.05, 0, 1) ** 0.5
    height = 0.7 * face + 0.2 * fbm(N, 10, 27, 3) - 0.4 * pits - 0.7 * mortar
    rough = 0.85 + 0.1 * fbm(N, 50, 28, 2)
    save("MuroConci", col, height, rough, 5.0)


def pietra_secco():
    """Dry-stone field wall: pale limestone stones of every shape, laid roughly in courses, rounded and weathered,
    with deep dark gaps and small wedge stones instead of mortar (the country walls around Mazzarino)."""
    rnd = random.Random(31)
    u, v = grid(N)
    size = 2.0
    # Seeds: loose courses 12-24 cm tall, stones 18-48 cm long, jittered; distances on the torus so it tiles.
    seeds = []
    y = 0.0
    while y < size - 0.1:
        h = rnd.uniform(0.12, 0.24)
        x = rnd.uniform(0, 0.3)
        while x < size - 0.1:
            w = rnd.uniform(0.18, 0.48)
            seeds.append(((x + w / 2) / size, (y + h / 2 + rnd.uniform(-0.03, 0.03)) / size, w / h))
            x += w
        y += h
    # Warp the pixels a little so the outlines are irregular, not polygonal.
    wu = u + 0.006 * (fbm(N, 70, 41, 3) - 0.5)
    wv = v + 0.006 * (fbm(N, 70, 42, 3) - 0.5)
    d1 = np.full(u.shape, 9.0)
    d2 = np.full(u.shape, 9.0)
    ids = np.zeros(u.shape, np.int64)
    for k, (sx, sy, aspect) in enumerate(seeds):
        dx = np.abs(wu - sx)
        dx = np.minimum(dx, 1 - dx)
        dy = np.abs(wv - sy)
        dy = np.minimum(dy, 1 - dy)
        # Stones longer than tall: distances along U count less.
        d = np.sqrt((dx / np.sqrt(aspect)) ** 2 + (dy * np.sqrt(aspect)) ** 2) * size
        nearer = d < d1
        d2 = np.where(nearer, d1, np.minimum(d2, d))
        ids = np.where(nearer, k, ids)
        d1 = np.where(nearer, d, d1)
    edge = (d2 - d1) * 0.5                                    # metres to the gap, about
    r = block_rand(ids, 7)
    r2 = block_rand(ids, 13)
    pale = srgb_to_lin([216, 206, 182])
    warm = srgb_to_lin([204, 184, 146])
    grey = srgb_to_lin([178, 172, 158])
    col = pale[None, None, :] * (1 - r2[..., None]) + warm * (r2[..., None] * 0.6) + grey * (r2[..., None] * 0.4)
    col = col * (0.72 + 0.4 * r[..., None]) * (0.72 + 0.5 * fbm(N, 16, 43, 4))[..., None]
    # Weathering: darker grime on the lower part of each stone, lichen spots, pits.
    lich = np.clip((fbm(N, 18, 44, 3) - 0.68) * 7, 0, 1) * np.clip((block_rand(ids, 17) - 0.4) * 3, 0, 1)
    col = col * (1 - 0.45 * lich[..., None]) + srgb_to_lin([120, 118, 92]) * (0.45 * lich[..., None])
    pits = np.clip((pnoise(N, 3, 45) - 0.8) * 6, 0, 1)
    grain = fbm(N, 6, 51, 3)
    col = col * (1 - 0.3 * pits[..., None]) * (0.85 + 0.3 * grain[..., None]) * (0.9 + 0.2 * fbm(N, 22, 52, 3))[..., None]
    # Gaps: narrow, deep and dark; the stones darken towards them (rounded, shadowed edges).
    gap_w = 0.002 + 0.012 * fbm(N, 30, 46, 3) ** 2
    gap = np.clip(1 - (edge - gap_w) / 0.004, 0, 1)
    face = np.clip(edge / 0.05, 0, 1) ** 0.5
    col = col * (0.7 + 0.3 * face[..., None])
    dark = srgb_to_lin([52, 46, 38]) * (0.6 + 0.8 * fbm(N, 10, 48, 2))[..., None]
    col = col * (1 - gap[..., None]) + dark * gap[..., None]
    height = 0.9 * face + 0.3 * fbm(N, 12, 49, 3) + 0.15 * grain + 0.1 * r - 0.35 * pits - 1.0 * gap
    rough = 0.82 + 0.1 * fbm(N, 40, 50, 2) + 0.08 * gap
    save("PietraSecco", col, height, rough, 6.0)


def cemento():
    base = srgb_to_lin([152, 150, 142])
    blot = fbm(N, 300, 31, 5)
    col = base[None, None, :] * (0.78 + 0.35 * blot)[..., None]
    streak = fbm(N, 40, 32, 3, aniso=(6.0, 1.0))         # rain streaks down the wall (along V)
    col = col * (1 - 0.18 * np.clip(streak - 0.5, 0, 1)[..., None] * 2)
    pores = np.clip((pnoise(N, 1.5, 33) - 0.85) * 8, 0, 1)
    col = col * (1 - 0.4 * pores[..., None])
    height = 0.3 * fbm(N, 6, 34, 3) + 0.4 * blot - 0.5 * pores
    rough = 0.88 + 0.08 * fbm(N, 80, 35, 2)
    save("Cemento", col, height, rough, 3.0)


def legno():
    base = srgb_to_lin([118, 102, 82])
    grain = fbm(N, 30, 41, 4, aniso=(1.0, 20.0))         # fibres along U
    fine = fbm(N, 4, 42, 2, aniso=(1.0, 12.0))
    col = base[None, None, :] * (0.7 + 0.45 * grain + 0.1 * fine)[..., None]
    grey = srgb_to_lin([130, 128, 122])
    weather = np.clip(fbm(N, 200, 43, 3) * 1.8 - 0.5, 0, 1)
    col = col * (1 - 0.6 * weather[..., None]) + grey * 0.6 * weather[..., None]
    cracks = np.clip(1 - np.abs(fbm(N, 60, 44, 3, aniso=(1.0, 30.0)) - 0.5) / 0.01, 0, 1) * (fbm(N, 300, 45, 2) > 0.55)
    col = col * (1 - 0.6 * cracks[..., None])
    height = 0.5 * grain + 0.2 * fine - 0.8 * cracks
    rough = 0.8 + 0.1 * fine
    save("Legno", col, height, rough, 5.0)


def canna():
    """Giant reed (Arundo) for reed fences: fibres along V, a node every 25-35 cm, dry yellow to grey-brown,
    a few green-tinged canes. U runs round the cane (a cane is ~12 cm round, so U shows a slice)."""
    u, v = grid(N)
    fib = fbm(N, 6, 51, 3, aniso=(1.0, 25.0))
    tone = fbm(N, 300, 52, 3)
    dry = srgb_to_lin([176, 150, 96])
    grey = srgb_to_lin([128, 118, 96])
    green = srgb_to_lin([140, 140, 84])
    col = dry[None, None, :] * (1 - tone[..., None]) + grey * tone[..., None]
    g = np.clip(fbm(N, 500, 53, 2) * 2.5 - 1.4, 0, 1)
    col = col * (1 - 0.5 * g[..., None]) + green * 0.5 * g[..., None]
    col = col * (0.8 + 0.35 * fib[..., None])
    # Nodes: dark rings with a swelling; 3 per metre, not evenly spaced.
    nodes = np.zeros_like(v)
    for c in (0.11, 0.42, 0.74):
        d = np.abs(np.mod(v - c + 0.5, 1.0) - 0.5)
        nodes = np.maximum(nodes, np.clip(1 - d / 0.008, 0, 1))
    col = col * (1 - 0.55 * nodes[..., None])
    stain = np.clip(fbm(N, 80, 54, 3) * 2 - 1.1, 0, 1)
    col = col * (1 - 0.35 * stain[..., None])
    height = 0.3 * fib + 0.6 * nodes
    rough = 0.55 + 0.25 * fbm(N, 40, 55, 2)
    save("Canna", col, height, rough, 4.0)


def lastre_bianche():
    """White limestone slabs of the panelled roads: courses 30 cm deep across the road (V = along the road), slabs
    45-75 cm long, pale grey-cream with a tone per slab, dust and tyre grime, thin dark joints. The texture starts on
    a joint at U = 0 and V = 0, where the material puts the edge of the lava bands."""
    rows = [1.0] * 4                                         # 30 cm courses over 1.2 m
    _, block, dj, lu, lv = courses(rows, 1.2, (0.45, 0.75), 61)
    r = block_rand(block, 7)
    r2 = block_rand(block, 13)
    cream = srgb_to_lin([204, 196, 180])
    grey = srgb_to_lin([182, 180, 174])
    col = cream[None, None, :] * (1 - r2[..., None]) + grey * r2[..., None]
    col = col * (0.88 + 0.16 * r[..., None]) * (0.9 + 0.14 * fbm(N, 220, 62, 4))[..., None]
    # Dust and grime: soft dark patches, darker towards the joints where dirt settles.
    grime = np.clip(fbm(N, 140, 63, 4) * 2.2 - 1.0, 0, 1)
    col = col * (1 - 0.22 * grime[..., None])
    edge = np.clip(1 - dj / 0.025, 0, 1)
    col = col * (1 - 0.15 * edge[..., None])
    # Fine grain and a few fossil pits of the limestone.
    grain = fbm(N, 2.0, 64, 2)
    pits = np.clip((pnoise(N, 2.2, 65) - 0.82) * 7, 0, 1)
    col = col * (0.94 + 0.1 * grain[..., None]) * (1 - 0.25 * pits[..., None])
    joint_w = 0.003 + 0.002 * fbm(N, 40, 66, 2)
    joint = np.clip(1 - (dj - joint_w) / 0.003, 0, 1)
    jcol = srgb_to_lin([118, 114, 106]) * (0.8 + 0.3 * fbm(N, 25, 67, 3))[..., None]
    col = col * (1 - joint[..., None]) + jcol * joint[..., None]
    # Flat slabs with softly worn edges.
    face = np.clip(dj / 0.012, 0, 1) ** 0.5
    height = 0.5 * face + 0.08 * grain + 0.05 * r - 0.3 * pits - 0.8 * joint
    rough = 0.62 + 0.15 * grain + 0.15 * joint - 0.12 * (1 - grime) * fbm(N, 300, 68, 2)
    save("LastreBianche", col, height, rough, 4.0)


def cubetti_lavici():
    """Small lava setts of the bands between the white panels: 10 cm cubes in rows, grey speckled with black and
    white grains (like bush-hammered basalt), dark joints."""
    rows = [1.0] * 10                                        # 10 cm rows over 1 m
    _, block, dj, lu, lv = courses(rows, 1.0, (0.08, 0.13), 71)
    r = block_rand(block, 17)
    base = srgb_to_lin([122, 122, 120])
    col = base[None, None, :] * (0.78 + 0.35 * r[..., None]) * (0.9 + 0.15 * fbm(N, 25, 72, 3))[..., None]
    dark = np.clip((pnoise(N, 2.5, 73) - 0.68) * 8, 0, 1)
    light = np.clip((pnoise(N, 2.5, 74) - 0.72) * 8, 0, 1)
    col = col * (1 - 0.6 * dark[..., None]) + srgb_to_lin([200, 198, 194]) * 0.5 * light[..., None]
    joint_w = 0.002 + 0.002 * fbm(N, 30, 75, 2)
    joint = np.clip(1 - (dj - joint_w) / 0.003, 0, 1)
    jcol = srgb_to_lin([88, 88, 86]) * (0.8 + 0.3 * fbm(N, 20, 76, 3))[..., None]
    col = col * (1 - joint[..., None]) + jcol * joint[..., None]
    grain = fbm(N, 1.6, 77, 2)
    dome = np.clip(dj / 0.02, 0, 1) ** 0.6
    height = 0.5 * dome + 0.15 * grain - 0.2 * dark - 0.9 * joint
    rough = 0.7 + 0.15 * grain + 0.1 * joint
    save("CubettiLavici", col, height, rough, 6.0)


CANDIDATES = os.path.join(ROOT, "Saved", "Mazzarino80", "Stairs", "Candidates")
LAVICA_BOX = (640, 1060, 1480, 1900)   # the square of diagonal setts in the atlas of the hand-made lava road


def seamless(a, feather=0.10):
    """Makes a crop tile: blends it with a copy shifted by half, the copy filling a band along the edges."""
    h, w = a.shape[:2]
    s = np.roll(np.roll(a, h // 2, 0), w // 2, 1)
    y = np.minimum(np.arange(h), h - 1 - np.arange(h)) / (h * feather)
    x = np.minimum(np.arange(w), w - 1 - np.arange(w)) / (w * feather)
    m = np.clip(np.minimum(y[:, None], x[None, :]), 0, 1)
    m = (m * m * (3 - 2 * m))[..., None]
    return a * m + s * (1 - m)


def lavica():
    """The user's lava setts (RoadSource/Migrated Test2_diffuse, Normal2, Test2_rough), cut out of the road
    atlas and made seamless; exported by Saved/m80_export_candidates2.py."""
    def load(name):
        return np.asarray(Image.open(os.path.join(CANDIDATES, name + ".tga")).convert("RGB").crop(LAVICA_BOX)).astype(np.float64) / 255.0
    d, n, r = load("Test2_diffuse"), load("Normal2"), load("Test2_rough")
    d, n, r = seamless(d), seamless(n * 2 - 1), seamless(r)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    lum = d.mean(-1)
    ao = np.clip(0.55 + 0.45 * lum / max(lum.mean() * 1.4, 1e-3), 0.4, 1)
    os.makedirs(OUT, exist_ok=True)

    def out(arr, name):
        Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(os.path.join(OUT, name))
    out(d, "T_M80_Lavica_D.png")
    out(n * 0.5 + 0.5, "T_M80_Lavica_N.png")
    out(np.stack([ao, r[..., 0], np.zeros_like(ao)], -1), "T_M80_Lavica_ORM.png")
    print("ok Lavica")


if __name__ == "__main__":
    # Names on the command line make only those sets (e.g. lastre_bianche cubetti_lavici).
    ALL = (pietra_lavica, basolato, muro_conci, pietra_secco, cemento, legno, lavica, canna, lastre_bianche, cubetti_lavici)
    for fn in ALL:
        if len(sys.argv) < 2 or fn.__name__ in sys.argv[1:]:
            fn()
