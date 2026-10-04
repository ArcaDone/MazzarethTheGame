"""Blender 4.3: 80s shiny acetate tracksuit textures for the MetaHuman hoodie and cargo pants,
after the reference photo: purple with pink / cyan / lime bands (V on the chest, diagonals on sleeves
and legs), pink collar (the hood), white zip.

Run: blender -b --factory-startup --python m80_tracksuit.py -- <hoodie.fbx> <torso_basecolor.tga> <pants.fbx> <legs_basecolor.tga> <out_dir>
The garments keep their shape and UVs. Bands are defined in 3D (garment rest pose, cm) as continuous
fields per vertex, interpolated per pixel when painting UV triangles, so the edges stay crisp. The fold
and seam shading of the original texture is kept (high-pass of its luminance).
"""
import sys

import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
HOODIE, TORSO_TEX, PANTS, LEGS_TEX, OUT = args

PURPLE = (112, 30, 192)
PINK = (255, 42, 172)
CYAN = (38, 188, 236)
LIME = (186, 252, 40)
WHITE = (238, 238, 238)
RIB = (84, 22, 150)  # cuffs and waistband
SIZE = 2048

# Region ids
TORSO, SLEEVE, HOOD, LEG, RIBBED = 0, 1, 2, 3, 4


def load_mesh(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path, use_anim=False)
    obj = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    me = obj.data
    me.calc_loop_triangles()
    co = np.array([obj.matrix_world @ v.co for v in me.vertices], np.float64)
    uv_layer = me.uv_layers.active.data
    tris = np.array([t.vertices[:] for t in me.loop_triangles], np.int64)
    tri_uv = np.array([[uv_layer[l].uv[:] for l in t.loops] for t in me.loop_triangles], np.float64)
    if co[:, 2].max() - co[:, 2].min() < 5:
        co *= 100.0
    return co, tris, tri_uv


def axes(co):
    ext = co.max(0) - co.min(0)
    lat = 0 if ext[0] >= ext[1] else 1
    return lat, 1 - lat


def band(b, table):
    """table: list of (lo, hi, colour); returns colour index array (-1 = base)."""
    out = np.full(b.shape, -1)
    for i, (lo, hi, _) in enumerate(table):
        out[(b >= lo) & (b < hi)] = i
    return out


def hoodie_fields(co):
    lat, dep = axes(co)
    x, y, z = co[:, lat], co[:, dep], co[:, 2]
    region = np.full(len(co), TORSO)
    f1 = np.zeros(len(co))   # band coordinate
    f2 = np.zeros(len(co))   # |x| for the zip
    half = (x.max() - x.min()) / 2
    shoulder = max(20.0, half * 0.3)
    torso = np.abs(x) <= shoulder
    zt = z[torso]
    z_low, z_top = zt.min(), np.percentile(zt, 99.5)
    # Hood: everything high and behind/around the head; front = away from the hood.
    # Shoulder seam height: top of the garment just outside the shoulders; the hood starts above it.
    seam = (np.abs(x) > shoulder) & (np.abs(x) < shoulder + 10.0)
    z_sh = np.percentile(z[seam], 97) if seam.any() else z_low + 0.78 * (z_top - z_low)
    neck = z_sh + 3.0
    hood = torso & (z > neck)
    back_sign = np.sign(y[hood].mean() - y[torso & ~hood].mean()) or -1.0
    region[hood] = HOOD
    # Chest V: higher at the sides.
    zv = z_low + 0.45 * (neck - z_low)
    f1[torso] = z[torso] - zv - 0.75 * np.abs(x[torso])
    f2[:] = np.abs(x) + np.where(y * back_sign > 0, 1000.0, 0.0)  # zip only on the front
    region[torso & (z < z_low + 6.0)] = RIBBED
    for s in (-1.0, 1.0):
        m = (x * s) > shoulder
        if m.sum() < 20:
            continue
        p = co[m]
        c = p.mean(0)
        _, _, vt = np.linalg.svd(p - c, full_matrices=False)
        d = vt[0] if vt[0][lat] * s > 0 else -vt[0]
        t = (p - c) @ d
        up = np.array([0.0, 0.0, 1.0])
        ref = up - d * (up @ d)
        ref /= np.linalg.norm(ref)
        h = ((p - c) - np.outer(t, d)) @ ref
        u = (t - t.min()) / max(1e-3, t.max() - t.min())
        idx = np.where(m)[0]
        region[idx] = SLEEVE
        f1[idx] = u + 0.012 * h          # diagonal around the sleeve
        region[idx[u > 0.93]] = RIBBED   # cuff
    return region, f1, f2


def pants_fields(co):
    lat, dep = axes(co)
    x, z = co[:, lat], co[:, 2]
    region = np.full(len(co), LEG)
    f1 = np.zeros(len(co))
    zmin, zmax = z.min(), z.max()
    knee = zmin + 0.42 * (zmax - zmin)
    side = np.where(x >= 0, 1.0, -1.0)
    cx = np.where(x >= 0, np.median(x[x >= 0]), np.median(x[x < 0]))
    f1[:] = (z - knee) + 0.6 * (x - cx) * side   # rising towards the outside of each leg
    region[z > zmax - 5.0] = RIBBED
    region[z < zmin + 4.0] = RIBBED
    return region, f1, np.zeros(len(co))


CHEST = [(3.0, 7.5, PINK), (9.5, 14.0, CYAN), (16.0, 20.5, LIME)]
SLEEVE_BANDS = [(0.10, 0.17, LIME), (0.19, 0.26, PINK), (0.52, 0.59, PINK), (0.61, 0.68, LIME), (0.70, 0.77, CYAN)]
LEG_BANDS = [(-30.0, -25.0, CYAN), (-23.0, -18.0, LIME), (-16.0, -10.0, PINK), (14.0, 19.0, LIME), (21.0, 26.0, PINK)]


def colour(region, f1, f2):
    col = np.empty(region.shape + (3,), np.float32)
    col[:] = PURPLE
    for reg, table in ((TORSO, CHEST), (SLEEVE, SLEEVE_BANDS), (LEG, LEG_BANDS)):
        m = region == reg
        k = band(f1, table)
        for i, (_, _, c) in enumerate(table):
            col[m & (k == i)] = c
    col[region == HOOD] = PINK
    col[region == RIBBED] = RIB
    col[(region == TORSO) & (f2 < 0.8)] = WHITE   # zip
    return col


def detail(tex_path):
    img = bpy.data.images.load(tex_path)
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
    lum = px @ np.array([0.299, 0.587, 0.114], np.float32)
    k = 31
    pad = np.pad(lum, k, mode="edge")
    cs = np.cumsum(np.cumsum(pad, 0), 1)
    blur = (cs[2 * k:, 2 * k:] - cs[:-2 * k, 2 * k:] - cs[2 * k:, :-2 * k] + cs[:-2 * k, :-2 * k]) / ((2 * k) ** 2)
    shade = np.clip(lum / np.maximum(blur[:h, :w], 1e-3), 0.6, 1.3)
    if (w, h) != (SIZE, SIZE):
        shade = shade[(np.arange(SIZE) * h / SIZE).astype(int)][:, (np.arange(SIZE) * w / SIZE).astype(int)]
    return shade


def hood_islands(tris, tri_uv, region):
    """Whole UV islands that are mostly hood become hood (the hood hangs behind the back)."""
    parent = list(range(len(tris)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    owner = {}
    for f in range(len(tris)):
        for k in range(3):
            key = (int(tris[f][k]), round(tri_uv[f][k][0], 5), round(tri_uv[f][k][1], 5))
            if key in owner:
                ra, rb = find(f), find(owner[key])
                if ra != rb:
                    parent[ra] = rb
            else:
                owner[key] = f
    roots = np.array([find(f) for f in range(len(tris))])
    tri_hood = (region[tris] == HOOD).mean(1)
    tri_region = np.full(len(tris), -1)
    for r in np.unique(roots):
        m = roots == r
        if tri_hood[m].mean() > 0.35:
            tri_region[m] = HOOD
    return tri_region


def paint(tris, tri_uv, region, f1, f2, tex_path, out_path):
    shade = detail(tex_path)
    forced = hood_islands(tris, tri_uv, region)
    img_col = np.empty((SIZE, SIZE, 3), np.float32)
    img_col[:] = PURPLE
    for f in range(len(tris)):
        uv = tri_uv[f]
        px = uv[:, 0] * SIZE
        py = (1.0 - uv[:, 1]) * SIZE
        x0, x1 = int(max(0, np.floor(px.min()))), int(min(SIZE - 1, np.ceil(px.max())))
        y0, y1 = int(max(0, np.floor(py.min()))), int(min(SIZE - 1, np.ceil(py.max())))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        det = (py[1] - py[2]) * (px[0] - px[2]) + (px[2] - px[1]) * (py[0] - py[2])
        if abs(det) < 1e-9:
            continue
        l0 = ((py[1] - py[2]) * (gx - px[2]) + (px[2] - px[1]) * (gy - py[2])) / det
        l1 = ((py[2] - py[0]) * (gx - px[2]) + (px[0] - px[2]) * (gy - py[2])) / det
        l2 = 1 - l0 - l1
        inside = (l0 >= -0.02) & (l1 >= -0.02) & (l2 >= -0.02)
        if not inside.any():
            continue
        v = tris[f]
        lw = np.stack([l0, l1, l2], -1)
        reg = region[v][np.argmax(lw, -1)] if forced[f] < 0 else np.full(l0.shape, forced[f])
        a = l0 * f1[v[0]] + l1 * f1[v[1]] + l2 * f1[v[2]]
        b = l0 * f2[v[0]] + l1 * f2[v[1]] + l2 * f2[v[2]]
        c = colour(reg, a, b)
        sub = img_col[y0:y1 + 1, x0:x1 + 1]
        sub[inside] = c[inside]
    out = np.clip(img_col * shade[..., None], 0, 255) / 255.0
    img = bpy.data.images.new("out", SIZE, SIZE, alpha=False)
    img.pixels[:] = np.concatenate([out, np.ones((SIZE, SIZE, 1), np.float32)], 2)[::-1].ravel()
    img.filepath_raw = out_path
    img.file_format = "PNG"
    img.save()
    print("M80 wrote", out_path)


co, tris, tri_uv = load_mesh(PANTS)
paint(tris, tri_uv, *pants_fields(co), LEGS_TEX, OUT + "/T_M80_Tuta_Pantaloni_D.png")
co, tris, tri_uv = load_mesh(HOODIE)
paint(tris, tri_uv, *hoodie_fields(co), TORSO_TEX, OUT + "/T_M80_Tuta_Giacca_D.png")
