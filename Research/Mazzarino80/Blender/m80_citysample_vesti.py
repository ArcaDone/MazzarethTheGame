"""Blender 5.2: City Sample crowd garments (exported from the City Sample project by Scripts/m80_citysample_export.py)
fitted onto our MetaHumans and dressed in our fabrics, as parametric outfits like m80_vestiti.py's.

The City Sample garments are skinned to the same MetaHuman skeleton, in the same A pose, on bodies of their own
(the "body" mesh they ship is only the hands: the rest of the skin is cut away under the clothes). Each garment
follows the joints from their body to ours (every vertex moves by its bones' joint offsets, weighted by its skin
weights), then is pushed out of our body's skin. Skin pieces inside a garment mesh (legs under a skirt) are dropped.
Their UVs are an atlas: our fabric (a tiling texture of tile_m metres) repeats ColoreScala times per UV unit, and
the garment's own normal map (seams, wrinkles, buttons) and occlusion (packed A, red) come along for the Unreal
material M_M80_StoffaCS (Scripts/m80_vestiti_import.py).

Run: blender -b --factory-startup --python m80_citysample_vesti.py -- [Key,Key...]
Out: Saved/Mazzarino80/Folla/Vestiti/<Key>/ as m80_vestiti.py (SM_M80_<Key>{,_LOD1..3}.fbx, Textures/, <Key>.json)
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_folla_oggetti as common  # noqa: E402
import m80_vestiti as V  # noqa: E402

ROOT = common.ROOT
CS = os.path.join(ROOT, "Saved", "Mazzarino80", "CitySample")
OUT = V.OUT
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = [k for k in (ARGS[0].split(",") if ARGS else []) if k]
TEX = 512
LODS = [None, 9000, 4000, 1600]     # LOD0 as City Sample made it, then the crowd's budget
MARGIN = 0.008
# Layers within an outfit: key -> [(inner key, its slot or None for all, my slot or None for all)]: those faces of mine
# are kept LAYER_GAP out of the inner garment (a shirt tucked into a skirt or trousers, a jacket over the trousers).
LAYERS = {
    "CS_Pantaloni": [("CS_CamiciaGiacca", "Cotone_Camicia", None)],
    "CS_CamiciaGiacca": [("CS_Pantaloni", None, "Lana_Giacca")],
    "CS_Gonna": [("CS_Camicetta", None, None)],
}
# The crowd: shirts tucked in; jumpers, waistcoats, jackets and open shirts over the trousers (pairs worn together).
OLD_TROUSERS = ["CS_V_Pantaloni", "CS_V_PantaloniMarroni"]
for _k in OLD_TROUSERS:
    LAYERS[_k] = [("CS_V_Camicia", None, None)] + [(k, "Cotone_Camicia", None) for k in ("CS_V_Festa", "CS_V_Giacca", "CS_V_Gilet")]
LAYERS["CS_V_Festa"] = [(k, None, slot) for k in OLD_TROUSERS for slot in ("Lana_Gilet", "Lana_Giacca")]
LAYERS["CS_V_Giacca"] = [(k, None, "Lana_Giacca") for k in OLD_TROUSERS]
LAYERS["CS_V_Gilet"] = [(k, None, "Lana_Gilet") for k in OLD_TROUSERS]
LAYERS["CS_A_Gonna"] = [("CS_A_Camicia", None, None), ("CS_A_Dolcevita", None, None)]
LAYERS["CS_U_PantaloniGrigi"] = [("CS_U_Completo", "Cotone_Camicia", None)]
LAYERS["CS_U_Completo"] = [("CS_U_PantaloniGrigi", None, "Lana_Giacca")]
LAYERS["CS_U_Dolcevita"] = [("CS_U_PantaloniGrigi", None, None)]
LAYERS["CS_U_Maglione"] = [("CS_U_Pantaloni", None, None)]
LAYERS["CS_U_Quadri"] = [("CS_U_Jeans", None, None)]
LAYERS["CS_R_Maglione"] = [("CS_R_Jeans", None, None)]
LAYERS["CS_R_Camicia"] = [("CS_R_Jeans", None, None)]
LAYERS["CS_D_Dolcevita"] = [("CS_D_Pantaloni", None, None)]
LAYERS["CS_RA_Giacchino"] = [("CS_RA_Jeans", None, None)]
LAYERS["CS_RA_Camicia"] = [("CS_RA_Jeans", None, None)]
LAYERS["CS_RA_Gonna"] = [("CS_RA_Dolcevita", None, None)]
LAYER_GAP = 0.005
# Shoes: our MetaHumans' toes are longer and wider than City Sample's feet; moving the joints does not grow a shoe,
# so its front is grown until it covers the toes (TOE_ROOM inside its surface).
SHOES = {"CS_Stringate", "CS_Ballerine", "CS_V_Scarpe", "CS_A_Scarpe", "CS_U_Mocassini", "CS_U_Stringate", "CS_D_Mocassini",
         "CS_RA_Mocassini"}
TOE_ROOM = 0.004
TOES_LEFT = 0.01   # share of toe vertices allowed out: the push out of the skin that follows takes care of them
LAYER_REACH = 0.03
CACHE = {}      # key -> [(slot, vertices, faces)] of the garments built in this run, world space

# Our fabric for each City Sample material, by a word of its name: (slot name, kind, colour(s), tile metres).
# The slot name's prefix picks the fabric preset in Unreal (Lana, Cotone, Maglia, Seta, Jeans, Cuoio).
GARMENTS = {
    "CS_CamiciaGiacca": ("Sandro", "m_tal_nrw_buttonDown_tie_blazer", {
        "buttonDown": ("Cotone_Camicia", "weave", (0.62, 0.72, 0.84), 0.05),
        "Suspenders": ("Seta_Cravatta", "regimental", ((0.30, 0.06, 0.07), (0.75, 0.68, 0.50)), 0.12),
        "blazer": ("Lana_Giacca", "tweed", ((0.24, 0.22, 0.20), (0.36, 0.33, 0.29), (0.15, 0.14, 0.13)), 0.12),
    }),
    "CS_Pantaloni": ("Sandro", "m_tal_nrw_slacks_belt", {
        "slacks": ("Lana_Pantaloni", "weave", (0.20, 0.19, 0.18), 0.04),
        "socks": ("Maglia_Calze", "knit", (0.06, 0.06, 0.07), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.20, 0.11, 0.06), 0.2),
    }),
    "CS_Stringate": ("Sandro", "m_tal_nrw_oxfords", {
        "oxford": ("Cuoio_Scarpe", "leather", (0.12, 0.06, 0.035), 0.15),
    }),
    "CS_Camicetta": ("Donna1", "f_tal_nrw_buttonDown", {
        "buttonDown": ("Cotone_Camicetta", "weave", (0.90, 0.86, 0.78), 0.05),
    }),
    "CS_Gonna": ("Donna1", "f_tal_nrw_skirt", {
        "skirt": ("Lana_Gonna", "tartan", ((0.22, 0.20, 0.30), [(0.0, 0.1, (0.45, 0.12, 0.12), 0.6),
                                                                 (0.5, 0.04, (0.75, 0.65, 0.40), 0.5)]), 0.15),
    }),
    "CS_Ballerine": ("Donna1", "f_tal_nrw_dressFlats", {
        "": ("Cuoio_Ballerine", "leather", (0.10, 0.07, 0.06), 0.15),
    }),
    # --- The whole crowd (fitted on the four reference bodies, resized by the Creator to the others) ---
    # Old men (Anziano1): white shirts, dark Sunday suits, waistcoats; coppola and cloak come from m80_vestiti.py.
    "CS_V_Camicia": ("Anziano1", "m_tal_nrw_buttonDown", {
        "buttonDown": ("Cotone_Camicia", "weave", (0.86, 0.85, 0.80), 0.05),
    }),
    "CS_V_Festa": ("Anziano1", "m_tal_nrw_buttonDown_tie_vest_blazer", {
        "buttonDown": ("Cotone_Camicia", "weave", (0.88, 0.87, 0.83), 0.05),
        "Suspenders": ("Seta_Cravatta", "regimental", ((0.10, 0.09, 0.09), (0.30, 0.28, 0.26)), 0.12),
        "vest": ("Lana_Gilet", "tweed", ((0.17, 0.17, 0.18), (0.25, 0.25, 0.26), (0.11, 0.11, 0.12)), 0.12),
        "blazer": ("Lana_Giacca", "tweed", ((0.17, 0.17, 0.18), (0.25, 0.25, 0.26), (0.11, 0.11, 0.12)), 0.12),
    }),
    "CS_V_Giacca": ("Anziano1", "m_tal_nrw_buttonDown_blazer", {
        "buttonDown": ("Cotone_Camicia", "weave", (0.70, 0.74, 0.78), 0.05),
        "blazer": ("Lana_Giacca", "tweed", ((0.27, 0.20, 0.14), (0.38, 0.30, 0.21), (0.18, 0.13, 0.09)), 0.12),
    }),
    "CS_V_Gilet": ("Anziano1", "m_tal_nrw_buttonDown_tie_vest", {
        "buttonDown": ("Cotone_Camicia", "weave", (0.90, 0.88, 0.82), 0.05),
        "Suspenders": ("Seta_Cravatta", "regimental", ((0.07, 0.07, 0.07), (0.22, 0.22, 0.22)), 0.12),
        "vest": ("Lana_Gilet", "knit", (0.24, 0.18, 0.13), 0.04),
    }),
    "CS_V_Pantaloni": ("Anziano1", "m_tal_nrw_slacks_belt", {
        "slacks": ("Lana_Pantaloni", "weave", (0.16, 0.16, 0.17), 0.04),
        "socks": ("Maglia_Calze", "knit", (0.05, 0.05, 0.06), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.08, 0.06, 0.05), 0.2),
    }),
    "CS_V_PantaloniMarroni": ("Anziano1", "m_tal_nrw_slacks_belt", {
        "slacks": ("Lana_Pantaloni", "weave", (0.25, 0.19, 0.13), 0.04),
        "socks": ("Maglia_Calze", "knit", (0.05, 0.05, 0.06), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.15, 0.09, 0.05), 0.2),
    }),
    "CS_V_Scarpe": ("Anziano1", "m_tal_nrw_oxfords", {
        "oxford": ("Cuoio_Scarpe", "leather", (0.05, 0.045, 0.04), 0.15),
    }),
    # Old women (Anziana1): all in black; headscarf, shawl and long black dress come from m80_vestiti.py.
    "CS_A_Camicia": ("Anziana1", "f_tal_nrw_buttonDown", {
        "buttonDown": ("Cotone_Camicetta", "weave", (0.07, 0.07, 0.075), 0.05),
    }),
    "CS_A_Dolcevita": ("Anziana1", "f_tal_nrw_turtleneck", {
        "turtleneck": ("Lana_Maglia", "knit", (0.10, 0.10, 0.11), 0.04),
    }),
    "CS_A_Gonna": ("Anziana1", "f_tal_nrw_skirt", {
        "skirt": ("Lana_Gonna", "weave", (0.08, 0.08, 0.085), 0.04),
    }),
    "CS_A_Scarpe": ("Anziana1", "f_tal_nrw_loafers", {
        "": ("Cuoio_Scarpe", "leather", (0.05, 0.045, 0.04), 0.15),
    }),
    # Men (Uomo2).
    "CS_U_Maglione": ("Uomo2", "m_tal_nrw_crewneck", {
        "crewneck": ("Lana_Maglione", "knit", (0.70, 0.62, 0.48), 0.04),
    }),
    "CS_U_Quadri": ("Uomo2", "m_tal_nrw_buttonOpen", {
        "buttonOpen": ("Cotone_Quadri", "tartan", ((0.55, 0.12, 0.10), [(0.0, 0.08, (0.12, 0.12, 0.25), 0.6),
                                                                       (0.5, 0.03, (0.85, 0.80, 0.70), 0.5)]), 0.12),
    }),
    "CS_U_Completo": ("Uomo2", "m_tal_nrw_buttonDown_tie_blazer", {
        "buttonDown": ("Cotone_Camicia", "weave", (0.90, 0.90, 0.88), 0.05),
        "Suspenders": ("Seta_Cravatta", "regimental", ((0.10, 0.12, 0.25), (0.55, 0.10, 0.10)), 0.12),
        "blazer": ("Lana_Giacca", "weave", (0.35, 0.35, 0.36), 0.05),
    }),
    "CS_U_Dolcevita": ("Uomo2", "m_tal_nrw_turtleneck_blazer", {
        "turtleneck": ("Lana_Maglia", "knit", (0.06, 0.06, 0.07), 0.04),
        "blazer": ("Lana_Giacca", "tweed", ((0.55, 0.42, 0.28), (0.65, 0.52, 0.36), (0.42, 0.31, 0.20)), 0.12),
    }),
    "CS_U_Pantaloni": ("Uomo2", "m_tal_nrw_slacks_belt", {
        "slacks": ("Lana_Pantaloni", "weave", (0.62, 0.55, 0.42), 0.04),
        "socks": ("Maglia_Calze", "knit", (0.20, 0.15, 0.10), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.20, 0.11, 0.06), 0.2),
    }),
    "CS_U_PantaloniGrigi": ("Uomo2", "m_tal_nrw_slacks_belt", {
        "slacks": ("Lana_Pantaloni", "weave", (0.33, 0.33, 0.34), 0.04),
        "socks": ("Maglia_Calze", "knit", (0.06, 0.06, 0.07), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.07, 0.06, 0.05), 0.2),
    }),
    "CS_U_Jeans": ("Uomo2", "m_tal_nrw_jeans_belt", {
        "jeans": ("Cotone_Jeans", "weave", (0.17, 0.25, 0.42), 0.04),
        "socks": ("Maglia_Calze", "knit", (0.85, 0.85, 0.83), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.25, 0.14, 0.07), 0.2),
    }),
    "CS_U_Mocassini": ("Uomo2", "m_tal_nrw_loafers", {
        "": ("Cuoio_Scarpe", "leather", (0.22, 0.12, 0.06), 0.15),
    }),
    "CS_U_Stringate": ("Uomo2", "m_tal_nrw_oxfords", {
        "oxford": ("Cuoio_Scarpe", "leather", (0.05, 0.045, 0.04), 0.15),
    }),
    # Young men (Uomo2): bright jumpers and shirts, stonewashed jeans.
    "CS_R_Maglione": ("Uomo2", "m_tal_nrw_crewneck", {
        "crewneck": ("Lana_Maglione", "knit", (0.70, 0.10, 0.10), 0.04),
    }),
    "CS_R_Camicia": ("Uomo2", "m_tal_nrw_buttonOpen", {
        "buttonOpen": ("Cotone_Camicia", "weave", (0.35, 0.70, 0.70), 0.05),
    }),
    "CS_R_Jeans": ("Uomo2", "m_tal_nrw_jeansLong_belt", {
        "jeans": ("Cotone_Jeans", "weave", (0.32, 0.42, 0.58), 0.04),
        "socks": ("Maglia_Calze", "knit", (0.85, 0.85, 0.83), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.10, 0.07, 0.05), 0.2),
    }),
    # Women (Donna1).
    "CS_D_Dolcevita": ("Donna1", "f_tal_nrw_turtleneck_blazer", {
        "turtleneck": ("Lana_Maglia", "knit", (0.85, 0.80, 0.70), 0.04),
        "blazer": ("Lana_Giacca", "weave", (0.10, 0.13, 0.25), 0.05),
    }),
    "CS_D_Pantaloni": ("Donna1", "f_tal_nrw_slacks_belt", {
        "slacks": ("Lana_Pantaloni", "weave", (0.55, 0.50, 0.42), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.30, 0.07, 0.08), 0.2),
    }),
    "CS_D_Mocassini": ("Donna1", "f_tal_nrw_loafers", {
        "": ("Cuoio_Scarpe", "leather", (0.30, 0.07, 0.08), 0.15),
    }),
    # Young women (Donna1).
    "CS_RA_Giacchino": ("Donna1", "f_tal_nrw_scoopneck_croppedJacket", {
        "scoopneck": ("Lana_Maglia", "knit", (0.88, 0.45, 0.60), 0.04),
        "croppedJacket": ("Cotone_Jeans", "weave", (0.30, 0.42, 0.62), 0.04),
    }),
    "CS_RA_Jeans": ("Donna1", "f_tal_nrw_jeans_belt", {
        "jeans": ("Cotone_Jeans", "weave", (0.20, 0.30, 0.50), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.85, 0.83, 0.80), 0.2),
    }),
    "CS_RA_Dolcevita": ("Donna1", "f_tal_nrw_turtleneck", {
        "turtleneck": ("Lana_Maglia", "knit", (0.90, 0.75, 0.20), 0.04),
    }),
    "CS_RA_Gonna": ("Donna1", "f_tal_nrw_skirt", {
        "skirt": ("Cotone_Jeans", "weave", (0.22, 0.32, 0.52), 0.04),
    }),
    "CS_RA_Camicia": ("Donna1", "f_tal_nrw_buttonOpen", {
        "buttonOpen": ("Cotone_Camicetta", "weave", (0.70, 0.60, 0.82), 0.05),
    }),
    "CS_RA_Mocassini": ("Donna1", "f_tal_nrw_loafers", {
        "": ("Cuoio_Scarpe", "leather", (0.85, 0.83, 0.80), 0.15),
    }),
}


def fabric_pixels(kind, spec, rng):
    if kind == "weave":
        return V.weave(TEX, spec, rng, scale=2, depth=0.05)
    if kind == "knit":
        return V.knit(TEX, spec, rng)
    if kind == "tweed":
        return common.tweed(TEX, spec, rng)
    if kind == "leather":
        return common.leather(TEX, spec, rng)
    if kind == "tartan":
        base, lines = spec
        return common.tartan(TEX, base, lines, rng)
    if kind == "regimental":
        a, b = spec
        y, x = np.mgrid[0:TEX, 0:TEX]
        band = ((x + y) % (TEX // 4)) < TEX // 24
        rgb = np.ones((TEX, TEX, 3)) * np.array(a)
        rgb[band] = b
        return rgb * (0.94 + 0.12 * common.noise(TEX, TEX, 48, rng)[..., None])
    raise ValueError(kind)


def joints(arm_ob):
    return {b.name: np.array((arm_ob.matrix_world @ b.head_local)[:]) for b in arm_ob.data.bones}


def report():
    with open(os.path.join(CS, "report.json"), encoding="utf-8") as f:
        return json.load(f)


def metres_per_uv(me, poly_ids):
    """Side of one UV unit in metres on these faces (3D area over UV area)."""
    uv = me.uv_layers[0].data
    a3 = auv = 0.0
    for i in poly_ids:
        p = me.polygons[i]
        a3 += p.area
        pts = [uv[li].uv for li in p.loop_indices]
        s = 0.0
        for k in range(len(pts)):
            x0, y0 = pts[k]
            x1, y1 = pts[(k + 1) % len(pts)]
            s += x0 * y1 - x1 * y0
        auv += abs(s) * 0.5
    return math.sqrt(a3 / auv) if auv > 1e-9 else 1.0


def layer_out(me, key):
    """Pushes my faces (or those of one slot) out of the inner garments of LAYERS already built in this run."""
    done = {"applied": [], "missing": []}
    for inner, inner_slot, my_slot in LAYERS.get(key, []):
        if inner not in CACHE:
            done["missing"].append(inner)
            continue
        verts, faces = [], []
        for slot, co, fs in CACHE[inner]:
            if inner_slot and slot != inner_slot:
                continue
            base = len(verts)
            verts.extend(co)
            faces.extend(tuple(i + base for i in f) for f in fs)
        if not faces:
            continue
        bvh = BVHTree.FromPolygons(verts, faces)
        mine = {i for i, m in enumerate(me.materials) if m and (my_slot is None or m.name.split(".")[0] == my_slot)}
        check = {vi for p in me.polygons if p.material_index in mine for vi in p.vertices}
        moved = 0
        for vi in check:
            v = me.vertices[vi]
            loc, nrm, _, _ = bvh.find_nearest(v.co, LAYER_REACH)
            if loc is None:
                continue
            d = (v.co - loc).dot(nrm)
            if d < LAYER_GAP:
                v.co = v.co + nrm * (LAYER_GAP - d)
                moved += 1
        me.update()
        done["applied"].append({"inner": inner, "moved": moved})
    return done


def fit_toes(co, faces, body):
    """Grows the front of each shoe (front = -Y), longer, a little wider and taller towards the tip, by the smallest step that
    leaves every toe vertex of our body inside it (by TOE_ROOM); returns the growth per side and the toes left out."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    out = {}
    for side in ("l", "r"):
        ankle, ball = body.joint.get("foot_" + side), body.joint.get("ball_" + side)
        if ankle is None or ball is None:
            continue
        d = ball - ankle
        d[2] = 0.0
        d /= np.linalg.norm(d)
        across = np.array([-d[1], d[0], 0.0])
        near = lambda pts: np.linalg.norm((pts - ball)[:, :2], axis=1) < 0.16  # noqa: E731
        foot = body.co[near(body.co) & (body.co[:, 2] < ball[2] + 0.06)]
        foot = foot[(foot - ankle) @ d > float((ball - ankle) @ d)]   # the toes: ahead of the ball joint
        shoe = near(co) & (co[:, 2] < ball[2] + 0.12)
        if not len(foot) or not shoe.any():
            continue
        base = co[shoe].copy()
        t = (base - ankle) @ d
        w = (base - ankle) @ across
        t_max = max(float(t.max()), 1e-3)
        sole = float(base[:, 2].min())
        idx = np.nonzero(shoe)[0]
        sub = {int(i): n for n, i in enumerate(idx)}
        polys = [f for f in faces if all(int(v) in sub for v in f)]

        def outside(k):
            grow = np.clip(t / t_max, 0.0, 1.0)[:, None]
            moved = base + np.outer(np.maximum(t, 0.0) * (k - 1.0), d) + grow * np.outer(w * (k - 1.0) * 0.6, across)
            moved[:, 2] += grow[:, 0] * (base[:, 2] - sole) * (k - 1.0) * 0.8   # a taller toe box too
            tree = BVHTree.FromPolygons([Vector(v) for v in moved], [[sub[int(v)] for v in f] for f in polys])
            # A toe vertex is inside when the shoe is in front of it, on both sides and above it (a lining makes the
            # nearest-face test useless); TOE_ROOM: the shoe must not be closer than that ahead.
            dirs = [Vector(d), Vector(across), Vector(-across), Vector((0.0, 0.0, 1.0))]
            left = 0
            for p in foot:
                v = Vector(p)
                for n, ray in enumerate(dirs):
                    hit = tree.ray_cast(v, ray, 0.25)
                    if hit[0] is None or (n == 0 and hit[3] < TOE_ROOM):
                        left += 1
                        break
            return moved, left

        best = None
        trail = []
        for k in np.arange(1.0, 1.31, 0.02):
            moved, left = outside(float(k))
            trail.append(left)
            if best is None or left < best[2]:
                best = (float(k), moved, left)
            if left <= TOES_LEFT * len(foot):
                break
        co[shoe] = best[1]
        out[side] = {"growth": round(best[0], 2), "toes_out": best[2], "toe_vertices": len(foot), "out_by_step": trail}
    return out


def build(key, target, source, fabrics, rep):
    body = V.Body(target)
    tgt = dict(body.joint)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CS, "fbx", source + ".fbx"))
    arm = next(o for o in bpy.context.selected_objects if o.type == "ARMATURE")
    ob = next(o for o in bpy.context.selected_objects if o.type == "MESH")
    src = joints(arm)
    world = ob.matrix_world.copy()
    ob.parent = None
    ob.matrix_world.identity()
    ob.data.transform(world)
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    bpy.data.objects.remove(arm)
    me = ob.data
    info_cs = rep["meshes"][source]["materials"]

    # Skin pieces out; the rest renamed to our fabric slots.
    skin = {i for i, m in enumerate(me.materials) if m and m.name.startswith("M_Body")}
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in skin], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    for i in reversed(range(len(me.materials))):
        if not any(p.material_index == i for p in me.polygons):
            ob.active_material_index = i
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.material_slot_remove()

    # Joint offsets from their body to ours, blended by the skin weights.
    groups = {g.index: g.name for g in ob.vertex_groups}
    delta = {gi: (tgt[n] - src[n]) for gi, n in groups.items() if n in tgt and n in src}
    co = np.array([v.co[:] for v in me.vertices])
    move = np.zeros_like(co)
    for v in me.vertices:
        tot = 0.0
        acc = np.zeros(3)
        for g in v.groups:
            d = delta.get(g.group)
            if d is not None and g.weight > 0:
                acc += d * g.weight
                tot += g.weight
        if tot > 0:
            move[v.index] = acc / tot
    co += move
    toes = fit_toes(co, [tuple(p.vertices) for p in me.polygons], body) if key in SHOES else None
    me.vertices.foreach_set("co", co.ravel())
    me.update()
    rep_key = {"source": source, "body": target, "moved_mm_max": round(float(np.linalg.norm(move, axis=1).max()) * 1000, 1),
               "toe_stretch": toes}

    bm = bmesh.new()
    bm.from_mesh(me)
    pushed = 0
    for v in bm.verts:
        loc, nrm, _, _ = body.bvh.find_nearest(v.co)
        if loc is None:
            continue
        d = (v.co - loc).dot(nrm)
        if d < MARGIN:
            v.co = v.co + nrm * (MARGIN - d)
            pushed += 1
    bm.to_mesh(me)
    bm.free()
    rep_key["pushed_out"] = pushed
    for o in list(ob.vertex_groups):
        ob.vertex_groups.remove(o)

    # Materials: ours, with the City Sample normal map and occlusion recorded for Unreal.
    rng = np.random.default_rng(abs(hash(key)) % (2 ** 32))
    cs_info = {}
    new_mats = []
    for idx, m in enumerate(me.materials):
        name = m.name if m else ""
        word = next((w for w in fabrics if w and w.lower() in name.lower()), "" if "" in fabrics else None)
        if word is None:
            word = next(iter(fabrics))
        slot, kind, spec, tile_m = fabrics[word]
        polys = [p.index for p in me.polygons if p.material_index == idx]
        mpu = metres_per_uv(me, polys) if polys else 1.0
        img = common.image(slot, fabric_pixels(kind, spec, rng))
        mat = common.material(slot, img=img, rough=0.85)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        tex = next(n for n in nodes if n.type == "TEX_IMAGE")
        mapping = nodes.new("ShaderNodeMapping")
        coord = nodes.new("ShaderNodeTexCoord")
        mapping.inputs["Scale"].default_value = (mpu / tile_m, mpu / tile_m, 1)
        links.new(coord.outputs["UV"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        mat.use_backface_culling = False
        new_mats.append(mat)
        csm = next((x for x in info_cs if x["name"] and x["name"].rsplit(".", 1)[-1] == name.split(".")[0]), None)
        texs = (csm or {}).get("textures", {})
        tga = lambda p: (p.rsplit(".", 1)[-1] + ".tga") if p else None  # noqa: E731
        cs_info[slot] = {"cs_material": name, "metres_per_uv": round(mpu, 4), "tile_m": tile_m,
                         "colour_scale": round(mpu / tile_m, 3), "normal": tga(texs.get("Tex_Normals")),
                         "packed": tga(texs.get("PACKED A"))}
    for i, m in enumerate(new_mats):
        me.materials[i] = m
    for p in me.polygons:
        p.use_smooth = True
    # Same slot twice (two City Sample materials onto one fabric) is fine: Unreal keeps both slots.
    rep_key["slots"] = cs_info
    rep_key["layers"] = layer_out(me, key)
    CACHE[key] = [(m.name.split(".")[0], [v.co.copy() for v in me.vertices],
                   [tuple(p.vertices) for p in me.polygons if p.material_index == i]) for i, m in enumerate(me.materials)]
    rep_key["triangles"] = sum(len(p.vertices) - 2 for p in me.polygons)

    out = os.path.join(OUT, key)
    os.makedirs(out, exist_ok=True)
    V.preview(body, [ob], os.path.join(out, "anteprima_"))
    bpy.data.objects.remove(body.ob)
    ob.name = me.name = "SM_M80_" + key
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(me)
    bm.free()
    common.OUT = OUT
    info = common.export(ob, key, {"body": target, "lods": LODS, "citysample": cs_info})
    for n, tris in enumerate(LODS[1:], start=1):
        lod = ob.copy()
        lod.data = ob.data.copy()
        bpy.context.scene.collection.objects.link(lod)
        V.decimate(lod, tris)
        lod.name = lod.data.name = "SM_M80_%s_LOD%d" % (key, n)
        bpy.ops.object.select_all(action="DESELECT")
        lod.select_set(True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(out, lod.name + ".fbx"), use_selection=True, apply_unit_scale=True,
                                 apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z",
                                 object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True,
                                 path_mode="COPY", embed_textures=False)
        info["lod%d_triangles" % n] = sum(len(p.vertices) - 2 for p in lod.data.polygons)
    with open(os.path.join(out, key + ".json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    rep_key["info"] = info
    print("VESTITO_CS", json.dumps(rep_key))
    return rep_key


def main():
    rep = report()
    done = {}
    for key, (target, source, fabrics) in GARMENTS.items():
        if ONLY and key not in ONLY:
            continue
        done[key] = build(key, target, source, fabrics, rep)
    # Second pass for the garments whose inner layer was built after them.
    for key, entry in list(done.items()):
        if entry["layers"]["missing"]:
            target, source, fabrics = GARMENTS[key]
            done[key] = build(key, target, source, fabrics, rep)
    with open(os.path.join(OUT, "citysample_report.json"), "w", encoding="utf-8") as f:
        json.dump(done, f, indent=1)


if __name__ == "__main__":
    main()
