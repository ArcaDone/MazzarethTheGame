"""Blender 5.2: the 24 Ore bar (D:/PerGioco/24ore/24ore_moderno.blend, the user's model of today's building) as it was
in the 1980s: same geometry, older textures, real size.

Run: blender -b "D:/PerGioco/24ore/24ore_moderno.blend" --python m80_24ore_vecchio.py -- [foto_dir]
- Size: the model's door is 1.54 m and its walls 2.5 m; scaled by SCALE the door is 2.3 m and the footprint
  (10.4 x 7 m) fills the OSM lot of the bar (way 1249072050, 11-12 x 5.5-6 m, Via Caltanissetta).
- Textures: every image a material uses gets an aged copy (at most 2048 px, so the 8.5k atlases shrink too):
  colours faded and greyer, a warm dust tint, broad damp patches and fine dirt (both from periodic noise, so the
  tiling textures still tile). Per material: plaster lighter but dirtier, the red mosaic of the base (a later
  renovation) turned into a grey-brown worn tile, the wooden frames darker and weathered, the gutters dull.
- The source file is never touched: saves D:/Mazzarino80_Sorgenti/Edifici/24ore/24ore_anni80.blend (refuses to
  overwrite it without M80_SOVRASCRIVI=1) with the aged images packed. With foto_dir: before/after views.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FOTO = ARGS[0] if ARGS else ""
DST = r"D:/Mazzarino80_Sorgenti/Edifici/24ore/24ore_anni80.blend"
SCALE = 1.5
MAX_PX = 2048
RNG = np.random.default_rng(80)

# per material: how much colour is kept, the tint mixed in, brightness, damp patches, fine dirt
AGING = {
    "WallPink": dict(sat=0.45, tint=(0.86, 0.82, 0.72), tint_mix=0.35, gain=0.90, patches=0.30, dirt=0.14),
    "House": dict(sat=0.55, tint=(0.80, 0.76, 0.68), tint_mix=0.25, gain=0.88, patches=0.20, dirt=0.10),
    "House2": dict(sat=0.50, tint=(0.80, 0.76, 0.68), tint_mix=0.35, gain=0.80, patches=0.30, dirt=0.14),
    "Mosaico Quadratini": dict(sat=0.18, tint=(0.52, 0.47, 0.42), tint_mix=0.55, gain=0.85, patches=0.25, dirt=0.14),
    "Wood": dict(sat=0.50, tint=(0.30, 0.22, 0.16), tint_mix=0.30, gain=0.70, patches=0.15, dirt=0.12),
}


def periodic_noise(h, w, scale_px):
    """Smooth noise in [0, 1] that wraps at the image edges (filtered in Fourier space), blobs about scale_px wide."""
    white = RNG.standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    sigma = 1.0 / max(scale_px, 1.0)
    filt = np.exp(-(fx * fx + fy * fy) / (2 * sigma * sigma))
    n = np.real(np.fft.ifft2(np.fft.fft2(white) * filt))
    n -= n.min()
    return n / max(n.max(), 1e-6)


def age(img, p):
    w, h = img.size
    if max(w, h) > MAX_PX:
        k = MAX_PX / max(w, h)
        img.scale(max(1, int(w * k)), max(1, int(h * k)))
        w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    rgb = px[..., :3]
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    rgb = lum[..., None] + (rgb - lum[..., None]) * p["sat"]
    rgb = rgb * (1 - p["tint_mix"]) + lum[..., None] * np.array(p["tint"], dtype=np.float32) * 1.6 * p["tint_mix"]
    broad = periodic_noise(h, w, w / 5.0)
    mid = periodic_noise(h, w, w / 24.0)
    patches = np.clip((broad * 0.7 + mid * 0.3 - 0.45) * 2.2, 0, 1)
    fine = periodic_noise(h, w, 1.5)
    dirt = np.clip((fine - 0.55) * 4.0, 0, 1)
    shade = 1.0 - p["patches"] * patches - p["dirt"] * dirt
    # damp patches go slightly brown-green, as old Sicilian plaster does
    damp = np.array([0.93, 0.92, 0.84], dtype=np.float32)
    rgb = rgb * shade[..., None] * (1 - patches[..., None] * (1 - damp) * 0.6)
    px[..., :3] = np.clip(rgb * p["gain"], 0, 1)
    img.pixels.foreach_set(px.ravel())
    img.update()


def aged_copy(src, p, done):
    key = (src.name, id(p))
    if key in done:
        return done[key]
    img = src.copy()
    img.name = os.path.splitext(src.name)[0] + "_anni80"
    age(img, p)
    img.filepath_raw = "//" + img.name + ".png"
    img.file_format = "PNG"
    img.pack()
    done[key] = img
    print("M80 invecchiata", src.name, "->", img.name, img.size[:])
    return img


def views(tag):
    sc = bpy.context.scene
    os.makedirs(FOTO, exist_ok=True)
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1400, 900
    sc.world = sc.world or bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.7, 0.75, 0.85, 1)
    bg.inputs[1].default_value = 1.5
    sun = bpy.data.objects.get("M80_Sole")
    if not sun:
        sun = bpy.data.objects.new("M80_Sole", bpy.data.lights.new("M80_Sole", "SUN"))
        sun.data.energy = 3
        sun.rotation_euler = (math.radians(50), 0, math.radians(30))
        sc.collection.objects.link(sun)
    objs = [o for o in sc.objects if o.type == "MESH"]
    pts = [o.matrix_world @ Vector(v) for o in objs for v in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2
    r = (hi - lo).length
    cam = bpy.data.objects.new("M80_Cam", bpy.data.cameras.new("M80_Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 30
    for a in (240, 300, 60):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0.12))
        cam.location = c + d * r * 0.8
        cam.location.z = lo.z + 1.7
        cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(FOTO, "%s_%03d.png" % (tag, a))
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bpy.data.objects.remove(sun)


def main():
    if os.path.exists(DST) and os.environ.get("M80_SOVRASCRIVI") != "1":
        print("M80 24ore_anni80.blend esiste gia': M80_SOVRASCRIVI=1 per rifarlo")
        return
    if FOTO:
        views("prima")
    # real size, scaled about the lowest point of the model (the ground stays at z = 0)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    zmin = min((o.matrix_world @ Vector(v)).z for o in objs for v in o.bound_box)
    S = Matrix.Translation((0, 0, -zmin * SCALE)) @ Matrix.Scale(SCALE, 4)
    for o in objs:
        if o.parent is None:
            o.matrix_world = S @ o.matrix_world
    done = {}
    for o in objs:
        for slot in o.material_slots:
            m = slot.material
            if not m or m.name not in AGING or not m.use_nodes:
                continue
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    n.image = aged_copy(n.image, AGING[m.name], done)
    for img in list(bpy.data.images):
        if img.users == 0:
            bpy.data.images.remove(img)
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=DST, copy=False)
    dims = [o.dimensions for o in objs]
    print("M80 salvato", DST, "dimensioni m", [tuple(round(v, 2) for v in d) for d in dims])
    if FOTO:
        views("dopo")


main()
