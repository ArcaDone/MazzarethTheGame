"""Churches (and the other hand-made buildings delivered as Blender packages in D:/BlenderTest/Da importare) made ready for
the game the way Palazzo Bartoli was (m80_bartoli_gioco.py): the package's low-poly geometry on the town's tiling texture
sets instead of its own baked atlases (a package's 11-17 atlases at 4096 px would weigh hundreds of MB a church; the sets
are shared by every building), a small dirt map per building (ambient occlusion + damp rising from the ground, 1024 px on
the lightmap UVs), UVs in metres, and the plan fitted on the church's OSM footprint.

Per building (CHIESE):
- source: the .blend and the collections of the game version (the packages' "07 LOW POLY" with materials per face; the
  older packages' "02 Asset Unreal"), objects left out by name;
- materials: the package's material name -> a tiling set (SLOT_RULES, overridden per building) and a tint;
- reductions: decimation of heavy relief per material (the rubble modelled stone by stone, the modelled coppi);
- bays: a band of the nave copied n times where the OSM footprint is longer than the photo estimate;
- placement: OSM id, rotation of the model (its +X is the facade) in the town's local frame (x east, y north), the model's
  plan centre on the footprint's centroid.
Meshes: SM_M80_<Key> (walls, stone, roofs: Nanite in Unreal) and SM_M80_<Key>_Dettagli (iron, glass, bells, doors:
LODs). New tiling sets (majolica, cotto, bricks) go next to Bartoli's in Textures/BartoliGioco (shared in Unreal).

Run (Blender 5.2: the packages are 5.2 files):
  D:/Blender/blender-5.2.2-windows-x64/blender.exe -b --factory-startup --python m80_chiese_gioco.py -- <Key>
Env: M80_SAMPLES (32), M80_NO_RENDER=1 (no previews).
Out: Saved/Mazzarino80/Chiese/<Key>/{SM_M80_<Key>.fbx, <Key>.json, <Key>_gioco.blend, anteprima_*.png},
     Textures/Chiese/T_M80_<Key>_Sporco.png
"""
import json
import math
import os
import re
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HERE)
import m80_bartoli_gioco as BG  # noqa: E402  (its main runs only with the argument "gioco")
import m80_arch_kit as K  # noqa: E402
import m80_arch_facade as A  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PKG = "D:/BlenderTest/Da importare"
SAVED = os.path.join(ROOT, "Saved", "Mazzarino80", "Chiese")
DIRT_TEX = os.path.join(HERE, "Textures", "Chiese")
PLAN = os.path.join(ROOT, "Research", "Mazzarino80", "building_footprint_plan.json")

# Package material (lower case, accents and punctuation ignored) -> slot of the game version. First match wins.
SLOT_RULES = [
    (r"fogliame|terriccio|studio|vegetaz|pianta|m18 terra", None),   # vegetation is Unreal's (user decision)
    (r"coppi|coppo|terracotta", "Coppi"),
    (r"pietra rustica|pietrame", "Pietrame"),
    (r"sagrato", "Sagrato"),
    (r"zoccolo|ocra", "Zoccolo"),
    (r"rosso ossido", "Intonaco_rosso"),
    (r"ottone", "Oro"),
    (r"castagno", "Legno"),
    (r"maiolica.*azzurr", "Maiolica_azzurro"),
    (r"intonaco|arriccio|malta", "Intonaco"),
    (r"maiolica.*avorio", "Maiolica_avorio"), (r"maiolica.*verde", "Maiolica_verde"),
    (r"maiolica.*antracite", "Maiolica_antracite"), (r"maiolica.*miele", "Maiolica_miele"),
    (r"maiolica.*terra", "Maiolica_terra"), (r"maiolica", "Maiolica_avorio"),
    (r"mattone", "Mattoni"),
    (r"cotto", "Cotto"),
    (r"legno verde|verde consunto", "Legno_verde"),
    (r"legno", "Legno"),
    (r"ferro|metal", "Ferro"),
    (r"bronzo", "Bronzo"),
    (r"oro", "Oro"),
    (r"vetro|glass", "Vetro"),
    (r"calcar|concio|arenaria|pietra|modanatur|cornic|giunti|stone", "Pietra"),
]
# Slot -> (kind, set, tint). Kinds: "set" (a tiling set), "flat" (colour, metal, roughness), "glass".
SLOTS = {
    "Pietra": ("set", "Arenaria", (1.12, 1.08, 1.0)),
    "Pietrame": ("set", "Pietrame_17_12", (1.1, 1.06, 0.98)),
    "Intonaco": ("set", "Intonaco", (1.08, 1.06, 1.0)),
    "Zoccolo": ("set", "Intonaco_giallo", None),
    "Sagrato": ("set", "Pietra_bianca", None),
    "Coppi": ("set", "Coppi", None),
    "Legno": ("set", "Legno_portone", None),
    "Legno_verde": ("set", "Persiane_verdi", None),
    "Ferro": ("set", "Ferro", None),
    "Mattoni": ("set", "Mattoni", None),
    "Cotto": ("set", "Cotto", None),
    "Maiolica_avorio": ("set", "Maiolica", (1.0, 0.95, 0.82)),
    "Maiolica_verde": ("set", "Maiolica", (0.25, 0.55, 0.32)),
    "Maiolica_antracite": ("set", "Maiolica", (0.18, 0.18, 0.19)),
    "Maiolica_miele": ("set", "Maiolica", (0.95, 0.66, 0.22)),
    "Maiolica_terra": ("set", "Maiolica", (0.62, 0.32, 0.17)),
    "Maiolica_azzurro": ("set", "Maiolica", (0.45, 0.60, 0.70)),
    "Intonaco_rosso": ("set", "Intonaco_rosso", None),
    "Bronzo": ("flat", (0.30, 0.20, 0.09), 1.0, 0.45),
    "Oro": ("flat", (0.62, 0.45, 0.16), 1.0, 0.3),
    "Vetro": ("glass", None, None),
}
DETAIL_SLOTS = {"Ferro", "Vetro", "Bronzo", "Oro"}

CHIESE = {
    "Immacolata": {
        "blend": PKG + "/parte 1/Chiesa_Immacolata_Concezione_Mazzarino/Chiesa_Immacolata_Concezione_Mazzarino.blend",
        "collections": ["02 "],
        "osm": "372573560",
        # Facade to the west (the bell tower at the back stands on Via Marino, east of the lot).
        "rotation_deg": 185,
        # The footprint is 36.8 m long, the photo estimate 25.5 m: two more bays of the side windows (5.5 m apart).
        "bays": {"from": -18.3, "to": -12.8, "count": 2},
        "slots": {"Legno": ("set", "Persiane_verdi", None)},   # the green door
        "decimate": {"Pietrame": 0.12},
    },
    "Lacrima": {
        "blend": PKG + "/parte 1/Chiesa_Maria_SS_della_Lacrima_Mazzarino/lowpoly/Chiesa_Lacrima_LOW_POLY.blend",
        "atlas_dir": PKG + "/parte 1/Chiesa_Maria_SS_della_Lacrima_Mazzarino/lowpoly/textures",
        "collections": ["07"], "exclude": ["Coppo_Modulo"],
        "osm": "375814227",
        # The convex facade and its stair stand at the corner of Via Pozzillo and Via delle Lacrime, west of the lot.
        "rotation_deg": 178,
        "decimate": {"Coppi": 0.5},
    },
    "SantaLucia": {
        "blend": PKG + "/parte2/Chiesa_Santa_Lucia_Mazzarino_Invecchiata/lowpoly/Chiesa_Santa_Lucia_LOW_POLY.blend",
        "atlas_dir": PKG + "/parte2/Chiesa_Santa_Lucia_Mazzarino_Invecchiata/lowpoly/textures",
        "collections": ["07"], "exclude": ["Coppo_Modulo"],
        "osm": "372574906",
        # Facade on Corso Vittorio Emanuele (Street View 127-162 Corso), the east end of the lot by the Corso.
        "rotation_deg": 4,
        "decimate": {"Coppi": 0.4},
    },
    "SpiritoSanto": {
        "blend": PKG + "/parte3/Chiesa_Spirito_Santo_Addolorata_Mazzarino/lowpoly/Chiesa_Spirito_Santo_LOW_POLY.blend",
        "atlas_dir": PKG + "/parte3/Chiesa_Spirito_Santo_Addolorata_Mazzarino/lowpoly/textures",
        "collections": ["07"], "exclude": ["Coppo_Modulo"],
        "osm": "375814238",
        # The rubble apse on the rounded east end of the footprint, the facade with the bell gable to the west.
        "rotation_deg": 181,
        # The sides and the apse are rubble under an eroded render (photos): rubble set, tinted from the atlases.
        "rules": [(r"malta erosa|giunti abside", "Pietrame")],
        "decimate": {"Bronzo": 0.3},
    },
    "Olmo": {
        "blend": PKG + "/parte2/Chiesa_Olmo_Mazzarino/Chiesa_Olmo_Mazzarino.blend",
        "collections": ["01", "02", "03", "04", "05", "06"],
        "osm": "372597217",
        # This older package has its facade towards -Y: turned so it looks east, to the road along the lot.
        "rotation_deg": 91, "facade_dir_deg": 270,
    },
    "SanGiuseppe": {
        "blend": PKG + "/parte4/San_Giuseppe_Mazzarino/San_Giuseppe_Mazzarino.blend",
        "collections": ["01", "02", "03", "04", "05", "06", "07", "08"],
        "osm": "375814268",
        # Its roof tiles are called "Cotto 00-05" in this package: coppi.
        "rules": [(r"cotto", "Coppi")],
        # Facade towards -Y in this package: turned so it looks east, to Via San Francesco da Paola / Via della Neve.
        "rotation_deg": 84, "facade_dir_deg": 270,
    },
    "SantIgnazio": {
        "blend": PKG + "/parte3/Complesso_Oratorio_Chiostro_SantIgnazio_Mazzarino/lowpoly/Complesso_LOW_POLY.blend",
        "collections": ["07"], "exclude": ["Coppo_Modulo"],
        "osm": "1249067242",
        "rotation_deg": 71,
        "decimate": {"Coppi": 0.3},
    },
}
AUTO_TINT = ("Intonaco", "Pietra", "Pietrame", "Zoccolo", "Sagrato")


# ---------------------------------------------------------------------------------------------
# New tiling sets (majolica tiles, cotto, bricks), next to Bartoli's

def majolica(U, V, period):
    """Glazed tiles 20 cm with a thin grout: the colour comes from the instance's tint (white glaze here)."""
    nu, w = K.cells(period[0], 0.2)
    nv, hgt = K.cells(period[1], 0.2)
    x, y = np.mod(U, w) / w, np.mod(V, hgt) / hgt
    edge = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    grout = edge < 0.03
    k = (np.floor(U / w).astype(np.int64) % nu) * 131 + np.floor(V / hgt).astype(np.int64) % nv
    jit = K._hash(k, k * 0 + 2, 9)
    glaze = (0.82 + 0.12 * jit)[..., None] * (0.92 + 0.1 * K.value_noise(U, V, 0.05, 31, 3, period))[..., None]
    col = np.where(grout[..., None], np.array([0.30, 0.27, 0.22]), np.array([0.80, 0.78, 0.72]) * glaze)
    h = np.where(grout, -0.003, 0.0015 * np.sin(math.pi * np.clip(edge / 0.5, 0, 1)))
    return h, col


def cotto(U, V, period):
    """Cotto: terracotta tiles 25 x 25 cm, uneven colour, worn edges."""
    nu, w = K.cells(period[0], 0.25)
    nv, hgt = K.cells(period[1], 0.25)
    x, y = np.mod(U, w) / w, np.mod(V, hgt) / hgt
    edge = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    k = (np.floor(U / w).astype(np.int64) % nu) * 97 + np.floor(V / hgt).astype(np.int64) % nv
    jit = K._hash(k, k * 0 + 3, 11)
    col = np.array([0.42, 0.19, 0.10]) * (0.75 + 0.4 * jit)[..., None] * (0.85 + 0.25 * K.value_noise(U, V, 0.06, 33, 3, period))[..., None]
    col = np.where((edge < 0.025)[..., None], np.array([0.30, 0.26, 0.20]), col)
    h = np.where(edge < 0.025, -0.003, 0.002 * K.value_noise(U, V, 0.02, 34, 2, period))
    return h, col


def bricks(U, V, period):
    """Thin bricks 25 x 5.5 cm in running bond, sandy mortar."""
    nv, course = K.cells(period[1], 0.065)
    nu, length = K.cells(period[0], 0.26)
    row = np.floor(V / course).astype(np.int64)
    uu = U + (row % 2) * length / 2
    x, y = np.mod(uu, length) / length, np.mod(V, course) / course
    mortar = (np.minimum(x, 1 - x) * length < 0.006) | (np.minimum(y, 1 - y) * course < 0.006)
    k = (np.floor(uu / length).astype(np.int64) % nu) * 53 + row % nv
    jit = K._hash(k, k * 0 + 4, 13)
    col = np.array([0.40, 0.17, 0.09]) * (0.7 + 0.5 * jit)[..., None]
    col = np.where(mortar[..., None], np.array([0.42, 0.37, 0.29]), col)
    h = np.where(mortar, -0.005, 0.001 * K.value_noise(U, V, 0.02, 35, 2, period))
    return h, col


def tile_set(name):
    """The tiling set of that name: Bartoli's when it exists, a new one for majolica, cotto and bricks."""
    if name == "Maiolica":
        return BG.texture_set(name, majolica, (1.2, 1.2), rough=(0.15, 0.6), px=1024)
    if name == "Cotto":
        return BG.texture_set(name, cotto, (1.5, 1.5), rough=(0.7, 0.9), px=1024)
    if name == "Mattoni":
        return BG.texture_set(name, bricks, (1.56, 1.56), rough=(0.75, 0.95), px=1024)
    files = ["T_%s_%s.png" % (name, k) for k in ("D", "N", "ORM")]
    if not all(os.path.exists(os.path.join(BG.TEX, f)) for f in files):
        raise RuntimeError("tiling set %s missing in %s (run m80_bartoli_gioco.py -- gioco)" % (name, BG.TEX))
    period = {"Coppi": (2.16, 2.1), "Ferro": (0.6, 0.6), "Legno_portone": (1.2, 1.2), "Legno_chiaro": (1.2, 1.2),
              "Persiane_verdi": (1.0, 1.0), "Telai": (1.0, 1.0), "Intonaco": (3.0, 3.0), "Intonaco_giallo": (3.0, 3.0),
              "Intonaco_rosso": (3.0, 3.0), "Pietrame_17_12": (2.4, 2.4), "Pietrame_16_11": (2.4, 2.4),
              "Pietrame_21_14": (2.4, 2.4), "Basolato": (2.52, 2.4), "Terra": (2.0, 2.0), "Ghiaia": (2.0, 2.0)}.get(name, (1.2, 1.2))
    BG.SETS[name] = {"period": list(period), "files": dict(zip(("D", "N", "ORM"), files))}
    return BG.SETS[name]


# ---------------------------------------------------------------------------------------------
# Geometry

def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("_", " "))


def slot_of(mat_name, extra=()):
    n = norm(mat_name)
    for rx, slot in list(extra) + SLOT_RULES:
        if re.search(rx, n):
            return slot
    return "Pietra"


def source_objects(cfg):
    out = []
    excl = cfg.get("exclude", [])
    for c in bpy.data.collections:
        if not any(c.name.startswith(p) for p in cfg["collections"]):
            continue
        for o in c.all_objects:
            if o.type != "MESH" or o.name.upper().startswith("UCX") or any(e in o.name for e in excl):
                continue
            if o.hide_render and not cfg.get("hidden_too"):
                continue
            if o not in out:
                out.append(o)
    return out


def copy_in_metres(ob, scale):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    if not me.polygons:
        bpy.data.meshes.remove(me)
        return None
    me.transform(Matrix.Scale(scale, 4) @ ob.matrix_world)
    if ob.matrix_world.determinant() < 0:
        me.flip_normals()
    out = bpy.data.objects.new(ob.name + "_g", me)
    bpy.context.scene.collection.objects.link(out)
    return out


def atlas_colours(ob, cfg):
    """sRGB colour of every face in the package's baked atlas (its UV_Bake), or None."""
    tex = cfg.get("atlas_dir")
    if not tex or "UV_Bake" not in ob.data.uv_layers:
        return None
    f = os.path.join(tex, ob.name[:-2].split(" ", 2)[-1] + "_BaseColor.png")
    if not os.path.exists(f):
        return None
    img = bpy.data.images.load(f)
    img.scale(512, 512)
    px = np.array(img.pixels[:], np.float32).reshape(512, 512, 4)[..., :3]
    bpy.data.images.remove(img)
    me = ob.data
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["UV_Bake"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    ls = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    cu = np.add.reduceat(uv, ls) / lt[:, None]
    col = px[np.clip((cu[:, 1] * 512).astype(int), 0, 511), np.clip((cu[:, 0] * 512).astype(int), 0, 511)]
    return np.clip(col, 0, 1) ** (1 / 2.2)


ATLAS_STATS = {}


def classify(ob, cfg):
    """Materials of the copy -> the game slots (one material per slot, named G_<slot>); faces of no slot removed.
    With the package's atlases: colour rules move faces between slots (white plaster painted on a "stone" material),
    and the slots' mean atlas colour is kept for the tints."""
    me = ob.data
    slots = [slot_of(m.name, cfg.get("rules", [])) if m else "Pietra" for m in me.materials]
    idx = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", idx)
    per_face = np.array(slots, dtype=object)[np.clip(idx, 0, len(slots) - 1)] if slots else np.array(["Pietra"] * len(idx), dtype=object)
    col = atlas_colours(ob, cfg)
    if col is not None:
        L = col.mean(1)
        ch = col.max(1) - col.min(1)
        for rule in cfg.get("colour_split", []):
            sel = (per_face == rule["from"]) & (L >= rule.get("L_min", 0)) & (L <= rule.get("L_max", 1)) &                   (ch >= rule.get("chroma_min", 0)) & (ch <= rule.get("chroma_max", 1))
            per_face[sel] = rule["to"]
        area = np.empty(len(me.polygons), np.float32)
        me.polygons.foreach_get("area", area)
        lin = col ** 2.2
        for s in set(per_face):
            if s:
                sel = per_face == s
                st = ATLAS_STATS.setdefault(s, [0.0, np.zeros(3)])
                st[0] += float(area[sel].sum())
                st[1] += (lin[sel] * area[sel, None]).sum(0)
    names = sorted({s for s in per_face if s})
    new = np.array([names.index(s) if s else -1 for s in per_face], np.int32)
    me.materials.clear()
    for s in names:
        me.materials.append(bpy.data.materials.get("G_" + s) or bpy.data.materials.new("G_" + s))
    me.polygons.foreach_set("material_index", np.maximum(new, 0))
    if (new < 0).any():
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(new < 0)[0]], context="FACES")
        bm.to_mesh(me)
        bm.free()
    me.update()


def roofs_up(ob, slots=("Coppi", "Cotto")):
    """Open roof pieces (tiles modelled as shells, roof sheets) whose faces look down are turned over: Unreal culls
    back faces, so a roof seen from above would vanish. Closed pieces (their normals sum to nothing) are left alone."""
    me = ob.data
    ks = {i for i, m in enumerate(me.materials) if m and m.name[2:] in slots}
    if not ks:
        return 0
    bm = bmesh.new()
    bm.from_mesh(me)
    todo = {f for f in bm.faces if f.material_index in ks}
    flipped = 0
    while todo:
        seed = todo.pop()
        part, stack = [seed], [seed]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in todo:
                        todo.discard(g)
                        part.append(g)
                        stack.append(g)
        area = sum(f.calc_area() for f in part)
        nz = sum(f.normal.z * f.calc_area() for f in part)
        if area > 0 and nz < -0.3 * area:
            bmesh.ops.reverse_faces(bm, faces=part)
            flipped += len(part)
    bm.to_mesh(me)
    bm.free()
    return flipped


def sky_up(ob):
    """Faces looking down with nothing above them are outer surfaces turned the wrong way (half a roof seen from the
    sky, a cornice top): Unreal would cull them. A ray straight up from each face looking down: no hit, turn it over.
    Undersides that belong (a slab's, an eave's, a tile's) always have their own top above them."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    up = Vector((0, 0, 1))
    wrong = []
    for f in bm.faces:
        if f.normal.z < -0.3:
            hit = tree.ray_cast(f.calc_center_median() + up * 0.003, up, 200.0)
            if hit[0] is None:
                wrong.append(f)
    if wrong:
        bmesh.ops.reverse_faces(bm, faces=wrong)
        bm.to_mesh(ob.data)
    bm.free()
    return len(wrong)


def decimate(ob, slot, ratio):
    """Collapse the faces of one slot to `ratio` of their triangles; vertices shared with other slots stay."""
    me = ob.data
    names = [m.name for m in me.materials]
    if "G_" + slot not in names:
        return
    k = names.index("G_" + slot)
    inside = np.ones(len(me.vertices), bool)
    touched = np.zeros(len(me.vertices), bool)
    tri_slot = 0
    tri_all = 0
    for p in me.polygons:
        t = len(p.vertices) - 2
        tri_all += t
        if p.material_index == k:
            tri_slot += t
            touched[list(p.vertices)] = True
        else:
            inside[list(p.vertices)] = False
    vg = ob.vertex_groups.new(name="decimate")
    vg.add([int(i) for i in np.nonzero(inside & touched)[0]], 1.0, "REPLACE")
    mod = ob.modifiers.new("dec", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.vertex_group = "decimate"
    mod.ratio = max(0.01, (tri_all - tri_slot * (1 - ratio)) / max(1, tri_all))
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if "decimate" in ob.vertex_groups:
        ob.vertex_groups.remove(ob.vertex_groups["decimate"])
    print("decimate %s %s: %d -> %d triangles" % (ob.name, slot, tri_all, sum(len(p.vertices) - 2 for p in me.polygons)))


def insert_bays(ob, band, count):
    """Copies the band x in [from, to] of the nave `count` times towards -X: what lies behind the band moves back."""
    a, b = band["from"], band["to"]
    w = b - a
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for x in (a, b):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    # Detach the band from both sides, then copy it and move the back part.
    on_cut = [e for e in bm.edges if all(abs(v.co.x - a) < 1e-4 for v in e.verts) or all(abs(v.co.x - b) < 1e-4 for v in e.verts)]
    bmesh.ops.split_edges(bm, edges=on_cut)
    band_faces = [f for f in bm.faces if a < f.calc_center_median().x < b]
    back_faces = [f for f in bm.faces if f.calc_center_median().x <= a]
    back_verts = {v for f in back_faces for v in f.verts}
    for v in back_verts:
        v.co.x -= count * w
    for k in range(1, count + 1):
        dup = bmesh.ops.duplicate(bm, geom=band_faces)
        for v in [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]:
            v.co.x -= k * w
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if any(abs(v.co.x - (a - k * w)) < 1e-3 for k in range(count + 1)) or abs(v.co.x - b) < 1e-3],
                             dist=0.001)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def metric_uvs(ob, lightmap):
    """UVMap in metres: u along the surface horizontally, v up its slope (walls: v up; roofs: v up the pitch, so the coppi
    run down it); faces lying flat take x, y. Sporco: the package's lightmap UVs (packed again after the joins)."""
    me = ob.data
    keep = me.uv_layers.get(lightmap) if lightmap else None
    if keep is not None:
        keep.name = "Sporco"
    for uv in list(me.uv_layers):
        if uv.name != "Sporco":
            me.uv_layers.remove(uv)
    if "Sporco" not in me.uv_layers:
        me.uv_layers.new(name="Sporco")
    me.uv_layers.new(name="UVMap")
    # UVMap first (UV0 in Unreal), Sporco second.
    bm = bmesh.new()
    bm.from_mesh(me)
    l0 = bm.loops.layers.uv["UVMap"]
    for f in bm.faces:
        n = f.normal
        if abs(n.z) > 0.92:
            U, V = Vector((1, 0, 0)), Vector((0, 1, 0))
        else:
            U = Vector((-n.y, n.x, 0)).normalized()
            V = n.cross(U).normalized()
        for lp in f.loops:
            lp[l0].uv = (lp.vert.co.dot(U), lp.vert.co.dot(V))
    bm.to_mesh(me)
    bm.free()
    names = [u.name for u in me.uv_layers]
    if names[0] != "UVMap":
        # Blender keeps creation order: rebuild Sporco after UVMap.
        data = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers["Sporco"].data.foreach_get("uv", data)
        me.uv_layers.remove(me.uv_layers["Sporco"])
        me.uv_layers.new(name="Sporco").data.foreach_set("uv", data)
    me.uv_layers["UVMap"].active = True


def join(objs, name):
    objs = [o for o in objs if o and o.data.polygons]
    if not objs:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = name
    return ob


def split_details(ob):
    """Faces of the detail slots into a second object."""
    me = ob.data
    det = [i for i, m in enumerate(me.materials) if m.name[2:] in DETAIL_SLOTS]
    if not det:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    for i in det:
        ob.active_material_index = i
        bpy.ops.object.material_slot_select()
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    other = [o for o in bpy.context.selected_objects if o != ob][0]
    for o in (ob, other):
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.material_slot_remove_unused()
    return other


def pack_lightmap(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    ob.data.uv_layers["Sporco"].active = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.data.uv_layers["UVMap"].active = True


def plan_centre(objs):
    """Centroid of the plan (everything 1 m above the base, 25 cm cells, holes filled) and the base height."""
    pts = []
    for o in objs:
        co = np.empty(len(o.data.vertices) * 3)
        o.data.vertices.foreach_get("co", co)
        pc = np.empty(len(o.data.polygons) * 3)
        o.data.polygons.foreach_get("center", pc)
        pts.append(np.vstack([co.reshape(-1, 3), pc.reshape(-1, 3)]))
    P = np.vstack(pts)
    z0 = np.percentile(P[:, 2], 0.5)
    Q = P[P[:, 2] > z0 + 1.0]
    cell = 0.25
    x0, y0 = Q[:, 0].min() - 2, Q[:, 1].min() - 2
    ix = ((Q[:, 0] - x0) / cell).astype(int)
    iy = ((Q[:, 1] - y0) / cell).astype(int)
    g = np.zeros((iy.max() + 10, ix.max() + 10), bool)
    g[iy, ix] = True

    def dil(a, n):
        for _ in range(n):
            b = a.copy()
            b[1:] |= a[:-1]; b[:-1] |= a[1:]; b[:, 1:] |= a[:, :-1]; b[:, :-1] |= a[:, 1:]
            a = b
        return a
    g = ~dil(~dil(g, 6), 6)
    out = np.zeros_like(g)
    H, W = g.shape
    stack = [(0, x) for x in range(W)] + [(H - 1, x) for x in range(W)] + [(y, 0) for y in range(H)] + [(y, W - 1) for y in range(H)]
    while stack:
        y, x = stack.pop()
        if 0 <= y < H and 0 <= x < W and not out[y, x] and not g[y, x]:
            out[y, x] = True
            stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    ys, xs = np.nonzero(~out)
    occ = ~out
    # 50 cm raster of the plan for the town scripts (which houses stand on the building).
    h2, w2 = occ.shape[0] // 2, occ.shape[1] // 2
    coarse = occ[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2).any(axis=(1, 3))
    raster = {"cell": 0.5, "x0": float(x0), "y0": float(y0), "w": int(w2), "h": int(h2),
              "rows": ["".join("1" if v else "0" for v in r) for r in coarse]}
    return [float(x0 + (xs.mean() + 0.5) * cell), float(y0 + (ys.mean() + 0.5) * cell)], float(z0), raster


def osm_centroid(osm_id):
    items = json.load(open(PLAN, encoding="utf-8-sig"))
    ring = next(it for it in items if str(it["id"]) == osm_id)["ring_cm"]
    r = np.array(ring, float)
    if np.hypot(*(r[0] - r[-1])) > 1e-6:
        r = np.vstack([r, r[:1]])
    x, y = r[:, 0], r[:, 1]
    a = x[:-1] * y[1:] - x[1:] * y[:-1]
    A_ = a.sum() / 2
    return [float(((x[:-1] + x[1:]) * a).sum() / (6 * A_)), float(((y[:-1] + y[1:]) * a).sum() / (6 * A_))]


# ---------------------------------------------------------------------------------------------
# Dirt map: ambient occlusion and damp from the ground, on the Sporco UVs

def bake_dirt(ob, key, z0, px=1024):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 64
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception:
        sc.cycles.device = "CPU"
    me = ob.data
    idx = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", idx)
    mats = list(me.materials)
    out = {}
    for kind in ("AO", "EMIT"):
        img = bpy.data.images.new("bake_" + kind, px, px, alpha=False, float_buffer=True)
        m = bpy.data.materials.new("bake_" + kind)
        m.use_nodes = True
        nt = m.node_tree
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.nodes.active = tex
        if kind == "EMIT":
            # Damp: 1 at the base, gone 1.6 m up.
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            sep = nt.nodes.new("ShaderNodeSeparateXYZ")
            mr = nt.nodes.new("ShaderNodeMapRange")
            mr.inputs["From Min"].default_value = z0 + 1.6
            mr.inputs["From Max"].default_value = z0
            em = nt.nodes.new("ShaderNodeEmission")
            nt.links.new(geo.outputs["Position"], sep.inputs[0])
            nt.links.new(sep.outputs[2], mr.inputs["Value"])
            nt.links.new(mr.outputs[0], em.inputs["Strength"])
            nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
        me.materials.clear()
        me.materials.append(m)
        me.polygons.foreach_set("material_index", np.zeros(len(me.polygons), np.int32))
        me.uv_layers["Sporco"].active = True
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        sc.cycles.bake_type = kind
        sc.render.bake.margin = 4
        bpy.ops.object.bake(type=kind, margin=4, uv_layer="Sporco")
        a = np.array(img.pixels[:]).reshape(px, px, 4)[..., 0]
        out[kind] = a
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", idx)
    me.uv_layers["UVMap"].active = True
    ao, damp = out["AO"], np.clip(out["EMIT"], 0, 1)
    # Gentle: the tiling sets carry their own occlusion; this adds the building's corners, eaves and the damp base.
    dirt = np.clip(0.62 + 0.38 * ao ** 1.2, 0, 1) * (1 - 0.2 * damp)
    os.makedirs(DIRT_TEX, exist_ok=True)
    name = "T_M80_%s_Sporco" % key
    img = bpy.data.images.new(name, px, px, alpha=False)
    img.colorspace_settings.name = "Non-Color"
    rgba = np.ones((px, px, 4), np.float32)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = dirt
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(DIRT_TEX, name + ".png")
    img.file_format = "PNG"
    img.save()
    return img


# ---------------------------------------------------------------------------------------------

def set_mean(tset):
    img = bpy.data.images.load(os.path.join(BG.TEX, tset["files"]["D"]), check_existing=True)
    img.scale(128, 128)
    px = np.array(img.pixels[:], np.float32).reshape(-1, 4)[:, :3]
    # 8-bit images give their stored sRGB values, float ones linear values.
    return (np.clip(px, 0, 1) if img.is_float else np.clip(px, 0, 1) ** 2.2).mean(0)


def auto_tint(slot, tset):
    """The tint that brings a tiling set to the colour the package's atlases give that slot, kept near the town's palette."""
    st = ATLAS_STATS.get(slot)
    if slot not in AUTO_TINT or not st or st[0] < 1.0:
        return None
    target = st[1] / st[0]
    t = np.clip(target / np.maximum(set_mean(tset), 1e-3), 0.75, 1.35)
    return [round(float(v), 3) for v in t]


def game_materials(objs, cfg, dirt):
    slots = dict(SLOTS)
    slots.update(cfg.get("slots", {}))
    info = {}
    for o in objs:
        for i, m in enumerate(o.data.materials):
            s = m.name[2:]
            kind = slots[s][0]
            if kind == "set":
                tset = tile_set(slots[s][1])
                tint = cfg.get("tints", {}).get(s) or auto_tint(s, tset) or slots[s][2]
                gm = BG.game_material("GM_%s_%s" % (cfg["key"], s), tset, tint, dirt if o.name.endswith(cfg["key"]) else None)
                info[s] = {"kind": "set", "set": slots[s][1], "tint": tint}
            elif kind == "flat":
                gm = bpy.data.materials.new("GM_%s_%s" % (cfg["key"], s))
                gm.use_nodes = True
                b = gm.node_tree.nodes["Principled BSDF"]
                b.inputs["Base Color"].default_value = (*slots[s][1], 1)
                b.inputs["Metallic"].default_value = slots[s][2]
                b.inputs["Roughness"].default_value = slots[s][3]
                info[s] = {"kind": "flat", "color": slots[s][1], "metal": slots[s][2], "rough": slots[s][3]}
            else:
                gm = bpy.data.materials.new("GM_%s_%s" % (cfg["key"], s))
                gm.use_nodes = True
                b = gm.node_tree.nodes["Principled BSDF"]
                b.inputs["Base Color"].default_value = (0.05, 0.06, 0.07, 1)
                b.inputs["Roughness"].default_value = 0.1
                info[s] = {"kind": "glass"}
            o.data.materials[i] = gm
    return info


def previews(objs, out_dir, centre_xy, size):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = int(os.environ.get("M80_SAMPLES", "32"))
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1280, 800
    sc.view_settings.exposure = -0.4
    if not sc.world:
        sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.72, 1)
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    sun = bpy.data.objects.new("SoleGioco", bpy.data.lights.new("SoleGioco", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    sc.collection.objects.link(sun)
    for o in sc.objects:
        if o.type in ("MESH", "CURVE", "FONT", "LIGHT") and o not in objs and o != sun:
            o.hide_render = True
    cam = bpy.data.objects.new("CamGioco", bpy.data.cameras.new("CamGioco"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cx, cy = centre_xy
    L = size
    views = {"tre_quarti": ((cx + 1.1 * L, cy - 0.9 * L, 0.45 * L), (cx, cy, 0.25 * L)),
             "facciata": ((cx + 1.4 * L, cy, 2.0), (cx, cy, 0.3 * L)),
             "fianco": ((cx, cy - 1.3 * L, 3.0), (cx, cy, 0.3 * L)),
             "retro_alto": ((cx - 1.0 * L, cy + 1.0 * L, 0.9 * L), (cx, cy, 0.2 * L))}
    for name, (eye, target) in views.items():
        cam.location = eye
        cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 28
        sc.render.filepath = os.path.join(out_dir, "anteprima_%s.png" % name)
        bpy.ops.render.render(write_still=True)


def build(key):
    t0 = time.time()
    cfg = dict(CHIESE[key], key=key)
    out_dir = os.path.join(SAVED, key)
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=cfg["blend"])
    bpy.context.scene.frame_set(1)          # animated doors closed
    src = source_objects(cfg)
    hmax = max((o.matrix_world @ Vector(c)).z for o in src for c in o.bound_box)
    scale = 0.01 if hmax > 200 else 1.0      # the packages are in centimetres
    lightmaps = {}
    copies = []
    for o in src:
        lm = next((u.name for u in o.data.uv_layers if "light" in u.name.lower()), None)
        cp = copy_in_metres(o, scale)
        if cp:
            classify(cp, cfg)
            n = roofs_up(cp)
            if n:
                print("roof faces turned up in %s: %d" % (cp.name, n))
            for slot, r in cfg.get("decimate", {}).items():
                decimate(cp, slot, r)
            lightmaps[cp.name] = lm
            copies.append(cp)
    for o in list(bpy.context.scene.objects):
        if o not in copies:
            o.hide_render = True
            o.hide_set(True)
    print("copied %d objects %.0f s" % (len(copies), time.time() - t0))
    for cp in copies:
        metric_uvs(cp, lightmaps[cp.name])
        if not lightmaps[cp.name]:
            # No lightmap UVs in the package: a quick unwrap for the dirt map.
            bpy.ops.object.select_all(action="DESELECT")
            cp.select_set(True)
            bpy.context.view_layer.objects.active = cp
            cp.data.uv_layers["Sporco"].active = True
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(island_margin=0.01)
            bpy.ops.object.mode_set(mode="OBJECT")
            cp.data.uv_layers["UVMap"].active = True
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    main = join(copies, "SM_M80_" + key)
    print("faces turned to the sky: %d" % sky_up(main))
    if cfg.get("bays"):
        insert_bays(main, cfg["bays"], cfg["bays"]["count"])
    det = split_details(main)
    if det:
        det.name = det.data.name = "SM_M80_%s_Dettagli" % key
    exported = [o for o in (main, det) if o]
    for o in exported:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.to_mesh(o.data)
        bm.free()
    pack_lightmap(main)
    centre, z0, raster = plan_centre([main])
    dirt = bake_dirt(main, key, z0)
    info = game_materials(exported, cfg, dirt)
    xs = [v.co.x for v in main.data.vertices]
    ys = [v.co.y for v in main.data.vertices]
    fd = math.radians(cfg.get("facade_dir_deg", 0.0))
    reach = max((x - centre[0]) * math.cos(fd) + (y - centre[1]) * math.sin(fd) for x, y in zip(xs, ys))
    front = [centre[0] + reach * math.cos(fd), centre[1] + reach * math.sin(fd)]
    tris = {o.name: len(o.data.polygons) for o in exported}
    print("triangles", tris, "%.0f s" % (time.time() - t0))
    bpy.ops.object.select_all(action="DESELECT")
    for o in exported:
        o.select_set(True)
    bpy.context.view_layer.objects.active = main
    fbx = "SM_M80_%s.fbx" % key
    bpy.ops.export_scene.fbx(filepath=os.path.join(out_dir, fbx), use_selection=True, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z", object_types={"MESH"},
                             mesh_smooth_type="FACE", bake_space_transform=True)
    manifest = {
        "key": key, "source": cfg["blend"], "osm_id": cfg["osm"], "fbx": fbx,
        "note": "model metres, +X = facade; place the pivot so model plan_centre lands on osm_centroid_world_cm after a "
                "rotation of rotation_deg (counter-clockwise, local frame x east y north; Unreal yaw = -rotation_deg); "
                "z: the ground under front_point at model z = base_z",
        "rotation_deg": cfg["rotation_deg"], "facade_dir_deg": cfg.get("facade_dir_deg", 0.0), "plan_centre_m": centre, "base_z_m": z0, "front_point_m": front,
        "osm_centroid_world_cm": osm_centroid(cfg["osm"]),
        "extent_m": [max(xs) - min(xs), max(ys) - min(ys)],
        "meshes": {o.name: {"triangles": tris[o.name], "slots": [m.name for m in o.data.materials],
                            "nanite": o is main} for o in exported},
        "materials": info, "sets": {k: v for k, v in BG.SETS.items()},
        "dirt": os.path.basename(dirt.filepath_raw), "dirt_dir": "Textures/Chiese", "plan_raster": raster,
    }
    with open(os.path.join(out_dir, key + ".json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, key + "_gioco.blend"))
    if os.environ.get("M80_NO_RENDER", "0") != "1":
        L = max(manifest["extent_m"])
        previews(exported, out_dir, centre, L)
    print("M80 chiesa %s in %.0f s" % (key, time.time() - t0))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for k in args:
        if k in CHIESE:
            build(k)
