"""Palazzo Bartoli for the game without baking: the modelled geometry itself (frames, cornices, carved consoles, balconies,
railings, shutters, doors, roofs) on tiling texture sets generated from the same stone, rubble and plaster functions as
the high-poly, plus a dirt map per facade over its wall.

Why not the bake (m80_bartoli_bake.py): one atlas per facade gave 128 px/m, flat-looking walls, consoles reduced to boxes,
black blotches where the bake rays met the dark plates behind the openings. Here every wall carries ~850 px/m of real
relief (normal + AO) that repeats, and the facade's own run-off streaks, patina and damp come from a 24 px/m dirt map.

- Facades are built in game mode (M80_GIOCO=1, m80_arch_facade.build): flat wall with its openings (UV0 in metres, UV1 over
  the facade for the dirt), the high-poly stone elements (weathered edges, carved consoles and keystones) with box UVs in
  metres in the facade's frame, the fittings (shutters, glass, doors, railings, eave tiles) as a second mesh per group.
- Texture sets (Textures/BartoliGioco/T_<set>_{D,N,ORM}.png, ORM = occlusion, roughness, metal): walls from
  A.surface(spec, period) grouped by kind (plaster sets tinted per facade), the stones of A.mats(), coppi, setts,
  gravel, soil, wood, painted wood, iron.
- Ground patches (courtyard, gardens) are their flat low versions on setts / gravel / soil, face up.
Run: blender -b --factory-startup --python m80_bartoli_gioco.py -- gioco
Env: M80_TILE_PX (2048), M80_VIEWS (preview views, comma separated), M80_SAMPLES (32), M80_INSEGNE=1 (shop signs back).
Out: Saved/Mazzarino80/Bartoli/bartoli_gioco.blend (collection "Gioco"), Gioco/<view>.png previews,
     Gioco/M80_Bartoli_Gioco.fbx + .json for Unreal (pivot at the lot origin, as the bake).
"""
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HERE)
os.environ.setdefault("M80_INTERNI", "0")
os.environ["M80_GIOCO"] = "1"   # read by m80_arch_facade at import
import m80_arch_kit as K  # noqa: E402
import m80_arch_facade as A  # noqa: E402
import m80_palazzo_bartoli as P  # noqa: E402  (stage "gioco" is not one of its own: importing it runs nothing)
import m80_bartoli_site as S  # noqa: E402

P.K = K
P.time = time
TEX = os.path.join(HERE, "Textures", "BartoliGioco")
OUT = os.path.join(P.SAVED, "Gioco")
PX = int(os.environ.get("M80_TILE_PX", "2048"))
PREFIX = "SM_M80_Bartoli_"
MASS_PREFIXES = ("Massa_", "Crema_parapetto", "B_muri_pensile", "Rudere_macerie", "Muro_cinta")
PATCHES = {"Cortile": "Basolato", "ghiaia": "Ghiaia", "aiuola": "Terra", "prato": "Terra"}
# Wall colour (gain on the linear albedo, saturation): between the town's Unreal materials (ashlar L 52, rubble L 54,
# plaster L 65) and the golden stone of the street photos (rubble L ~57 b ~25, the corner palace L ~66 b ~20), before
# the facade's dirt takes 3-5 L off. Measured on the tiles: rubble L 59 b 17, ashlar L 58 b 19, plaster L 71 b 15.
WALL_TONE = {"rubble": (0.8, 1.4), "ashlar": (0.8, 1.0), "plaster": (0.8, 1.2), "stone": (0.95, 1.0)}
SETS = {}


# ---------------------------------------------------------------------------------------------
# Tiling texture sets

def blur(h, sigma_px):
    """Gaussian blur that wraps around (the tile repeats)."""
    ky = np.fft.fftfreq(h.shape[0])[:, None]
    kx = np.fft.fftfreq(h.shape[1])[None, :]
    g = np.exp(-2 * (math.pi ** 2) * (sigma_px ** 2) * (kx ** 2 + ky ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(h) * g))


def save_image(name, arr, srgb):
    a = np.clip(arr, 0, 1)
    if srgb:
        a = a ** (1 / 2.2)
    h, w = a.shape[:2]
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=False)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :a.shape[2]] = a
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(TEX, name + ".png")
    img.file_format = "PNG"
    img.save()
    return img


def texture_set(name, fn, period, rough=(0.82, 0.95), normal_k=1.0, ao_k=1.0, sat=1.0, metal=None, px=PX, gain=1.0):
    """fn(U, V, period) -> (height m, linear albedo[, metal 0-1]) over one tile of period=(pu, pv) metres."""
    if name in SETS:
        return SETS[name]
    t = time.time()
    pu, pv = period
    names = ["T_%s_%s.png" % (name, k) for k in ("D", "N", "ORM")]
    if os.environ.get("M80_TILE_REBUILD", "0") != "1" and all(os.path.exists(os.path.join(TEX, n)) for n in names):
        # Already generated (M80_TILE_REBUILD=1 makes them again).
        SETS[name] = {"period": [round(pu, 4), round(pv, 4)], "files": dict(zip(("D", "N", "ORM"), names))}
        return SETS[name]
    u = (np.arange(px) + 0.5) * pu / px
    v = (np.arange(px) + 0.5) * pv / px
    U, V = np.meshgrid(u, v)
    res = fn(U, V, period)
    h, alb = res[0], res[1]
    met = res[2] if len(res) > 2 else (np.full(h.shape, metal) if metal else np.zeros(h.shape))
    dx, dy = pu / px, pv / px
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * dx)
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * dy)
    n = np.stack([-gx * normal_k, -gy * normal_k, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    # Occlusion and roughness from the cavities: joints and pits are darker and rougher.
    cav = blur(h, 0.012 / dx) - h
    cav2 = blur(h, 0.05 / dx) - h
    ao = np.clip(1 - ao_k * (np.maximum(cav, 0) * 30 + np.maximum(cav2, 0) * 10), 0.3, 1)
    r = rough[0] + (rough[1] - rough[0]) * np.clip(np.maximum(cav2, 0) * 80 + 0.3 * (1 - met), 0, 1)
    if sat != 1.0:
        lum = (alb * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
        alb = lum + (alb - lum) * sat
    alb = alb * gain
    files = {}
    for key, arr, srgb in (("D", alb, True), ("N", n * 0.5 + 0.5, False), ("ORM", np.stack([ao, r, met], -1), False)):
        img = save_image("T_%s_%s" % (name, key), arr, srgb)
        files[key] = os.path.basename(img.filepath_raw)
    SETS[name] = {"period": [round(pu, 4), round(pv, 4)], "files": files}
    print("set %s %.0f s" % (name, time.time() - t))
    return SETS[name]


def stone(base, dark, pitting, lichen=0.3):
    """The high-poly stone shader (A.stone_material) as a texture: mottled colour, lichen spots, pitting."""
    base, dark = np.array(base), np.array(dark)

    def fn(U, V, period):
        n = K.value_noise(U, V, 0.17, 5, 4, period)
        t = np.clip((n - 0.35) / 0.35, 0, 1)[..., None]
        col = dark + (base - dark) * t
        lm = np.clip((K.value_noise(U, V, 0.25, 9, 3, period) - 0.66) / 0.08, 0, 1)[..., None] * lichen
        col = col * (1 - lm) + np.array([0.20, 0.21, 0.15]) * lm
        pits = K.value_noise(U, V, 0.011, 7, 2, period)
        fine = K.value_noise(U, V, 0.006, 8, 2, period)
        big = K.value_noise(U, V, 0.08, 6, 3, period)
        hole = pits > 0.72
        h = 0.004 * big + pitting * 0.003 * (pits + fine) - pitting * 0.004 * hole
        col = col * (1 - 0.3 * pitting * hole)[..., None]
        return h, col
    return fn


def coppi(U, V, period):
    """Roof of coppi: alternate rows of channels and covers, each tile overlapping the one below."""
    nu, pair = K.cells(period[0], 0.36)
    nr, L = K.cells(period[1], 0.42)
    half = pair / 2
    pu = np.mod(U, pair)
    up = pu >= half
    x = np.mod(pu, half) / half
    k = (np.floor(U / pair).astype(np.int64) % nu) * 2 + up
    row = np.floor(V / L).astype(np.int64) % nr
    fv = np.mod(V, L) / L
    arc = np.sin(math.pi * x)
    jit = K._hash(k, row, 3)
    h = np.where(up, 0.055 * arc, 0.02 - 0.02 * arc) + 0.012 * fv + 0.012 * (1 - fv) ** 6 * up
    h = h + 0.004 * (jit - 0.5)
    col = np.array([0.36, 0.16, 0.09]) * (0.72 + 0.45 * jit)[..., None] * (0.85 + 0.25 * K.value_noise(U, V, 0.08, 4, 3, period))[..., None]
    # Channels hold dirt; covers bleach; lichen in yellow-grey spots.
    col = col * np.where(up, 1.0, 0.72)[..., None]
    moss = np.clip((K.value_noise(U, V, 0.25, 6, 3, period) - 0.6) * 5, 0, 1)[..., None] * 0.55
    col = col * (1 - moss) + np.array([0.33, 0.31, 0.20]) * moss
    edge = np.clip(1 - np.minimum(x, 1 - x) / 0.05, 0, 1)
    h = h - 0.006 * edge
    return h, col


def setts(U, V, period):
    h, _ = A.ashlar(U, V, course=0.24, length=0.42, seed=3, period=period)
    alb = np.ones(h.shape + (3,)) * np.array([0.075, 0.07, 0.065]) * (0.8 + 0.4 * K.value_noise(U, V, 0.15, 4, 3, period))[..., None]
    joints = h < 0.001
    alb = np.where(joints[..., None], np.array([0.16, 0.14, 0.11]), alb)
    return h * 0.8, alb


def soil(U, V, period):
    n = K.value_noise(U, V, 0.1, 8, 4, period)
    h = 0.02 * K.value_noise(U, V, 0.2, 7, 3, period) + 0.004 * K.value_noise(U, V, 0.01, 9, 2, period)
    alb = np.array([0.16, 0.11, 0.07]) * (0.75 + 0.5 * n)[..., None]
    return h, alb


def gravel(U, V, period):
    hs, sid, edge = K.rubble(U, V, cell=(0.025, 0.02), seed=21, mortar=0.002, period=period)
    alb = np.array([0.42, 0.36, 0.27]) * (0.65 + 0.6 * sid)[..., None]
    return hs * 0.5, alb


def wood(base, plank=0.12, worn=0.15):
    base = np.array(base)

    def fn(U, V, period):
        nu, w = K.cells(period[0], plank)
        x = np.mod(U, w) / w
        k = np.floor(U / w).astype(np.int64) % nu
        grain = K.value_noise(U * 25.0, V * 0.8, 0.5, 11, 4, (period[0] * 25.0, period[1] * 0.8))
        rnd = K._hash(k, k * 0 + 1, 5)
        joint = np.clip(1 - np.minimum(x, 1 - x) / 0.03, 0, 1)
        col = base * (0.75 + 0.5 * grain)[..., None] * (0.85 + 0.3 * rnd)[..., None] * (1 - 0.5 * joint)[..., None]
        bleach = np.clip((K.value_noise(U, V, 0.3, 12, 3, period) - 0.55) * 3, 0, 1)[..., None] * worn
        col = col * (1 - bleach) + np.array([0.30, 0.27, 0.22]) * bleach
        h = 0.002 * grain - 0.004 * joint
        return h, col
    return fn


def painted(color, worn=0.12):
    """Paint on wood, flaking where the weather hits: the grey wood shows through."""
    color = np.array(color)

    def fn(U, V, period):
        grain = K.value_noise(U * 25.0, V * 0.8, 0.5, 13, 4, (period[0] * 25.0, period[1] * 0.8))
        flake = K.value_noise(U, V, 0.12, 14, 4, period) + 0.15 * K.value_noise(U, V, 0.02, 15, 2, period)
        bare = np.clip((flake - (0.8 - 0.25 * worn)) * 12, 0, 1)
        wood_col = np.array([0.10, 0.09, 0.075]) * (0.8 + 0.4 * grain)[..., None]
        paint = color * (0.88 + 0.2 * K.value_noise(U, V, 0.3, 16, 3, period))[..., None]
        col = paint * (1 - bare[..., None]) + wood_col * bare[..., None]
        h = 0.0008 * grain - 0.0006 * bare
        return h, col
    return fn


def iron(U, V, period):
    rust = np.clip((K.value_noise(U, V, 0.08, 17, 4, period) - 0.66) * 5, 0, 1)
    col = np.array([0.035, 0.035, 0.035]) * (1 - rust[..., None]) + np.array([0.20, 0.09, 0.04]) * rust[..., None]
    h = 0.0015 * K.value_noise(U, V, 0.01, 18, 3, period) + 0.001 * rust
    return h, col, 0.7 * (1 - rust)


def plaster_set(name, color, seed, peel):
    gain, sat = WALL_TONE["plaster"]
    # Fewer, smaller patches of bare rubble than on the high-poly: on a tile they repeat.
    return texture_set(name, lambda U, V, p: A.plaster(U, V, color, peel * 0.4, seed, p), (3.0, 3.0), sat=sat, gain=gain)


def wall_set(spec):
    """Tiling set of a facade's wall and the tint that brings it to the facade's own colour."""
    w = spec.get("wall", {"type": "rubble"})
    t = w.get("type", "rubble")
    if t == "ashlar":
        c, l_ = w.get("course", 0.33), w.get("length", 0.62)
        nm = "Conci_%d_%d" % (round(c * 100), round(l_ * 100))
        period = (K.cells(2.4, l_)[0] * l_, K.cells(2.4, c)[0] * c)
        gain, sat = WALL_TONE["ashlar"]
        return texture_set(nm, lambda U, V, p: A.ashlar(U, V, c, l_, 4, p), period, sat=sat, gain=gain), None
    if t == "plaster":
        col = w.get("color", (0.62, 0.55, 0.42))
        red = col[0] > 2.5 * col[1]
        ref = (0.44, 0.11, 0.08) if red else (0.70, 0.62, 0.46)
        s = plaster_set("Intonaco_rosso" if red else "Intonaco", ref, 41 if red else 21, 0.3)
        return s, [round(col[i] / ref[i], 3) for i in range(3)]
    cell = tuple(w.get("cell", (0.21, 0.14)))
    mortar = w.get("mortar", 0.016)
    nm = "Pietrame_%d_%d" % (round(cell[0] * 100), round(cell[1] * 100))

    def fn(U, V, p):
        h, sid, edge = K.rubble(U, V, cell=cell, seed=7, mortar=mortar, period=p)
        alb = K.rubble_albedo(U, V, h, sid, edge, 7, p)
        # The mortar sits back in the joints, in shade and dirty, sandy like the stones: a darker warm line, not the
        # pale grey web of a crazy paving.
        joint = np.array([0.36, 0.28, 0.17]) * (0.8 + 0.35 * K.value_noise(U, V, 0.05, 23, 3, p))[..., None]
        return h, np.where((edge < 0)[..., None], joint, alb)
    gain, sat = WALL_TONE["rubble"]
    return texture_set(nm, fn, (2.4, 2.4), sat=sat, gain=gain, ao_k=1.5), None


# Material of the model -> (set, tint, flat). Flat materials keep their Blender colour (glass, brass, dark interiors).
STONES = {"Arenaria_hi": ((0.46, 0.34, 0.19), (0.33, 0.23, 0.12), 0.35), "Arenaria_portale_hi": ((0.48, 0.26, 0.09), (0.32, 0.16, 0.05), 0.45),
          "Pietra_bianca_hi": ((0.62, 0.58, 0.50), (0.48, 0.44, 0.38), 0.25), "Pietra_lavica_hi": ((0.07, 0.07, 0.07), (0.035, 0.035, 0.035), 0.6),
          "Intonaco_giallo_hi": ((0.55, 0.38, 0.10), (0.44, 0.29, 0.07), 0.15), "Marmo_hi": ((0.62, 0.61, 0.58), (0.52, 0.51, 0.48), 0.08)}
FLAT = ("Vetro", "Ottone", "Interno_buio", "Nero_opaco", "Acqua")


def set_for(mat_name, color):
    base = mat_name.split(".")[0]
    if base in STONES:
        b, d, p = STONES[base]
        gain, sat = WALL_TONE["stone"]
        return texture_set(base.replace("_hi", ""), stone(b, d, p), (1.2, 1.2), sat=sat, gain=gain), None
    if base in ("Coppi", "Coppi_tetto"):
        return texture_set("Coppi", coppi, (2.16, 2.1), rough=(0.7, 0.9)), None
    if base in ("Legno_portone", "Legno_chiaro"):
        return texture_set(base, wood(color), (1.2, 1.2), rough=(0.55, 0.75), px=1024), None
    if base in ("Persiane_verdi", "Telai"):
        return texture_set(base, painted(color), (1.0, 1.0), rough=(0.45, 0.7), px=1024), None
    if base in ("Ferro", "Serranda"):
        return texture_set("Ferro", iron, (0.6, 0.6), rough=(0.45, 0.8), px=1024), None
    if base in ("Pietrame_interno", "Macerie", "Cotto_facciata", "Interno"):
        return wall_set({"wall": {"type": "rubble"}})
    if base == "Terreno":
        return texture_set("Terra", soil, (2.0, 2.0)), None
    # Plastered things (belvedere, cream parapet, anything else plain): the plaster set in their colour.
    ref = (0.70, 0.62, 0.46)
    return plaster_set("Intonaco", ref, 21, 0.3), [round(min(2.0, color[i] / ref[i]), 3) for i in range(3)]


def base_color(mat):
    if mat and mat.use_nodes:
        b = mat.node_tree.nodes.get("Principled BSDF")
        if b:
            return tuple(b.inputs["Base Color"].default_value)[:3]
    return (0.5, 0.5, 0.5)


def game_material(name, tset, tint=None, dirt=None, flat=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = nodes["Principled BSDF"]
    if flat is not None:
        src = flat.node_tree.nodes.get("Principled BSDF") if flat.use_nodes else None
        if src:
            for k in ("Base Color", "Roughness", "Metallic", "Emission Color", "Emission Strength"):
                bsdf.inputs[k].default_value = src.inputs[k].default_value
        m["m80_flat"] = True
        return m
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tset["period"][0], 1 / tset["period"][1], 1)
    links.new(uv.outputs[0], mp.inputs[0])

    def tex(key, colour):
        t = nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, tset["files"][key]), check_existing=True)
        t.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        links.new(mp.outputs[0], t.inputs[0])
        return t
    td, tn, to = tex("D", True), tex("N", False), tex("ORM", False)
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(to.outputs[0], sep.inputs[0])
    col = td.outputs[0]

    def multiply(a, b):
        mx = nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        links.new(a, mx.inputs[6])
        if isinstance(b, (tuple, list)):
            mx.inputs[7].default_value = (*b, 1)
        else:
            links.new(b, mx.inputs[7])
        return mx.outputs[2]
    if tint:
        col = multiply(col, tuple(tint))
    col = multiply(col, sep.outputs[0])
    if dirt is not None:
        uv1 = nodes.new("ShaderNodeUVMap")
        uv1.uv_map = "Sporco"
        tdirt = nodes.new("ShaderNodeTexImage")
        tdirt.image = dirt
        tdirt.extension = "EXTEND"
        links.new(uv1.outputs[0], tdirt.inputs[0])
        col = multiply(col, tdirt.outputs[0])
    links.new(col, bsdf.inputs["Base Color"])
    links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    nm = nodes.new("ShaderNodeNormalMap")
    links.new(tn.outputs[0], nm.inputs["Color"])
    links.new(nm.outputs[0], bsdf.inputs["Normal"])
    m["m80_set"] = json.dumps({"set": tset, "tint": tint})
    return m


# ---------------------------------------------------------------------------------------------
# Game meshes

def evaluated_copy(ob, name):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=False, depsgraph=dg)
    if not me.polygons:
        bpy.data.meshes.remove(me)
        return None
    me.transform(ob.matrix_world)
    if ob.matrix_world.determinant() < 0:
        me.flip_normals()
    out = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(out)
    return out


def set_uvs(ob, frame_inv, wall=None):
    """UVMap: metres, projected on the dominant axis of each face in the facade frame (u along the facade, v up);
    Sporco: the facade's dirt map (u/W, v/H), for walls only (elsewhere a white corner of it is never sampled)."""
    me = ob.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    uv0 = me.uv_layers.new(name="UVMap")
    uv1 = me.uv_layers.new(name="Sporco")
    bm = bmesh.new()
    bm.from_mesh(me)
    l0 = bm.loops.layers.uv["UVMap"]
    l1 = bm.loops.layers.uv["Sporco"]
    rot = frame_inv.to_3x3()
    for f in bm.faces:
        n = rot @ f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            p = frame_inv @ lp.vert.co
            if ax == 1:
                a, b = p.x, p.z
            elif ax == 0:
                a, b = p.y, p.z
            else:
                a, b = p.x, p.y
            lp[l0].uv = (a, b)
            lp[l1].uv = (p.x / wall[0], p.z / wall[1]) if wall else (0.0, 0.0)
    bm.to_mesh(me)
    bm.free()
    del uv0, uv1


def assign(ob, slot_map):
    """Replaces the model's materials by their game versions (slot_map: old material name -> new material)."""
    me = ob.data
    for i, m in enumerate(me.materials):
        if m is not None and m.name in slot_map:
            me.materials[i] = slot_map[m.name]


def join(objs, name):
    objs = [o for o in objs if o]
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


def game_mat_for(mat, dirt_key=None, dirt=None, wall_spec=None):
    """Game material for one material of the model (walls: per facade, with the facade's dirt and tint)."""
    if wall_spec is not None:
        tset, tint = wall_set(wall_spec)
        return game_material("G_Muro_" + wall_spec["name"], tset, tint, dirt)
    if mat is None:
        return None
    base = mat.name.split(".")[0]
    if base in FLAT or base.endswith(("_fondo", "_lettere", "_bandiera", "_T")):
        return game_material("G_" + base, None, flat=mat)
    tset, tint = set_for(base, base_color(mat))
    key = "G_%s" % base if not tint else "G_%s_%s" % (base, "_".join("%d" % round(c * 100) for c in tint))
    return game_material(key, tset, tint)


def groups():
    names = []
    for c in bpy.data.collections:
        if c.name.endswith("_High") and c.name != "Tetti_High":
            n = c.name[:-5]
            if bpy.data.collections.get(n + "_Low") or bpy.data.collections.get(n + "_Detail"):
                names.append(n)
    return sorted(names)


def build_group(name, built, game_col):
    hi = bpy.data.collections.get(name + "_High")
    lo = bpy.data.collections.get(name + "_Low")
    de = bpy.data.collections.get(name + "_Detail")
    F = built.get(name)
    frame_inv = F.frame.matrix_world.inverted() if F else Matrix.Identity(4)
    wall = (F.width, F.height) if F else None
    pieces, fittings = [], []
    lows = {o.name: o for o in (lo.objects if lo else [])}
    for ob in list(hi.objects) if hi else []:
        if ob.type not in ("MESH", "CURVE") or ob.hide_render:
            continue
        twin = lows.get(ob.name[:-3]) if ob.name.endswith("_hi") else None
        if twin is not None and ob.type == "MESH" and len(ob.data.polygons) > 20000:
            # Ground patches: the flat low surface on a tiling texture, facing up.
            cp = evaluated_copy(twin, twin.name + "_g")
            kind = next((v for k, v in PATCHES.items() if k in twin.name), "Terra")
            tset = texture_set(kind, {"Basolato": setts, "Ghiaia": gravel, "Terra": soil}[kind], (2.52, 2.4) if kind == "Basolato" else (2.0, 2.0),
                               rough=(0.55, 0.9) if kind == "Basolato" else (0.85, 0.97))
            for p in cp.data.polygons:
                if p.normal.z < 0:
                    p.flip()
            cp.data.materials.clear()
            cp.data.materials.append(game_material("G_" + kind, tset))
            set_uvs(cp, Matrix.Identity(4))
            pieces.append(cp)
            continue
        cp = evaluated_copy(ob, ob.name + "_g")
        if not cp:
            continue
        set_uvs(cp, frame_inv, None)
        assign(cp, {m.name: game_mat_for(m) for m in cp.data.materials if m})
        pieces.append(cp)
    if F:
        for ob in (lo.objects if lo else []):
            if ob.name.endswith("_muro"):
                cp = evaluated_copy(ob, ob.name + "_g")
                set_uvs(cp, frame_inv, wall)
                cp.data.materials.clear()
                cp.data.materials.append(game_mat_for(None, dirt=getattr(F, "dirt", None), wall_spec=F.spec))
                pieces.append(cp)
    for ob in list(de.objects) if de else []:
        if ob.type not in ("MESH", "CURVE", "FONT") or ob.hide_render:
            continue
        cp = evaluated_copy(ob, ob.name + "_g")
        if not cp:
            continue
        set_uvs(cp, frame_inv, None)
        assign(cp, {m.name: game_mat_for(m) for m in cp.data.materials if m})
        fittings.append(cp)
    out = []
    for objs, nm in ((pieces, PREFIX + name), (fittings, PREFIX + name + "_Dettagli")):
        ob = join(objs, nm)
        if ob:
            for c in list(ob.users_collection):
                c.objects.unlink(ob)
            game_col.objects.link(ob)
            out.append(ob)
    return out


def build_rest(game_col):
    """Roofs (coppi on their slope UVs in metres), ridge rows, the volumes behind the facades."""
    sc = bpy.context.scene
    out = []
    roofs = [evaluated_copy(o, o.name + "_g") for o in bpy.data.collections["Tetti_Low"].objects if o.type == "MESH"]
    roof = join(roofs, PREFIX + "Tetti")
    if roof:
        roof.data.materials.clear()
        roof.data.materials.append(game_mat_for(bpy.data.materials.get("Coppi") or A.mats()["coppi"]))
        if "UVMap" not in roof.data.uv_layers:
            set_uvs(roof, Matrix.Identity(4))
        else:
            roof.data.uv_layers["UVMap"].active = True
            if "Sporco" not in roof.data.uv_layers:
                roof.data.uv_layers.new(name="Sporco")
        out.append(roof)
    ridges = []
    for o in bpy.data.collections["Tetti_High"].objects:
        if o.type == "CURVE" and not o.hide_render:
            cp = evaluated_copy(o, o.name + "_g")
            if cp:
                set_uvs(cp, Matrix.Identity(4))
                cp.data.materials.clear()
                cp.data.materials.append(game_mat_for(A.mats()["coppi"]))
                ridges.append(cp)
    r = join(ridges, PREFIX + "Tetti_Colmi")
    if r:
        out.append(r)
    mass = []
    for o in list(sc.collection.objects):
        if o.type == "MESH" and o.name.startswith(MASS_PREFIXES) and not o.name.endswith("_g"):
            cp = evaluated_copy(o, o.name + "_g")
            if cp:
                set_uvs(cp, Matrix.Identity(4))
                assign(cp, {m.name: game_mat_for(m) for m in cp.data.materials if m})
                mass.append(cp)
    v = join(mass, PREFIX + "Volumi")
    if v:
        out.append(v)
    for ob in out:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        game_col.objects.link(ob)
    return out


def previews(views):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = int(os.environ.get("M80_SAMPLES", "32"))
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.exposure = -0.4
    cam = bpy.data.objects.get("CamGioco") or bpy.data.objects.new("CamGioco", bpy.data.cameras.new("CamGioco"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    for name, (eye, target, fov) in views.items():
        cam.location = eye
        cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens_unit = "FOV"
        cam.data.angle = math.radians(fov)
        sc.render.filepath = os.path.join(OUT, "%s.png" % name)
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            # The GPU is shared with the Unreal editor: on "out of GPU memory" go on with the processor.
            print("render on CPU:", e)
            sc.cycles.device = "CPU"
            bpy.ops.render.render(write_still=True)
        print("render", name)


def main():
    t0 = time.time()
    os.makedirs(TEX, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    built = P.build_all(0.03)
    print("built %.0f s" % (time.time() - t0))
    game_col = bpy.data.collections.new("Gioco")
    bpy.context.scene.collection.children.link(game_col)
    exported = []
    for name in groups():
        exported += build_group(name, built, game_col)
        print("group %s %.0f s" % (name, time.time() - t0))
    exported += build_rest(game_col)
    # Only the game version in view and in the renders.
    for lc in bpy.context.view_layer.layer_collection.children:
        if lc.name not in ("Gioco", "Vicini"):
            lc.exclude = True
    for o in bpy.context.scene.collection.objects:
        if o.type in ("MESH", "CURVE", "FONT") and not o.name.startswith("Terreno") and o.name not in ("Terreno",):
            o.hide_render = o.hide_viewport = True
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in exported}
    manifest = {"units": "cm", "origin_world_cm": P.LAYOUT["origin_world_cm"],
                "note": "every mesh has its pivot at origin_world_cm: place them all there with no rotation",
                "meshes": {o.name: {"triangles": tris[o.name], "slots": [m.name for m in o.data.materials if m]} for o in exported},
                "sets": SETS,
                "materials": {m.name: json.loads(m.get("m80_set", "null") or "null") for m in bpy.data.materials if m.name.startswith("G_")},
                "dirt": {m.name: os.path.basename(n.image.filepath_raw) for m in bpy.data.materials if m.name.startswith("G_Muro_")
                         for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.name.endswith("_sporco")}}
    for img in bpy.data.images:
        if img.name.endswith("_sporco"):
            img.filepath_raw = os.path.join(TEX, img.name + ".png")
            img.file_format = "PNG"
            img.save()
    print("triangles %d" % sum(tris.values()))
    bpy.ops.object.select_all(action="DESELECT")
    for o in exported:
        o.select_set(True)
    bpy.context.view_layer.objects.active = exported[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "M80_Bartoli_Gioco.fbx"), use_selection=True, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z", object_types={"MESH"},
                             mesh_smooth_type="FACE", bake_space_transform=True)
    manifest["fbx"] = "M80_Bartoli_Gioco.fbx"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(P.SAVED, "bartoli_gioco.blend"))
    with open(os.path.join(OUT, "M80_Bartoli_Gioco.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    g = lambda x, y, h=1.6: P.ground(x, y) + h  # noqa: E731
    views = dict(P.photo_views())
    views["salita_cinema"] = ((-41.5, -20.0, g(-41.5, -20.0)), (-45.0, -1.0, 7.0), 80)
    views["corso_d"] = ((30.0, -38.0, g(30.0, -38.0)), (24.0, -18.0, 8.0), 90)
    views["balcone_vicino"] = ((32.0, -25.5, 6.5), (34.0, -15.0, 6.5), 60)
    only = [v for v in os.environ.get("M80_VIEWS", "frontale_bartoli,corso_222,angolo_farmacia,corso_d,balcone_vicino,salita_cinema,salita_teatro,cortile_scalone,aereo_sudest").split(",") if v]
    previews({k: v for k, v in views.items() if k in only and v[0] != "PN"})
    print("M80 Bartoli gioco in %.0f s" % (time.time() - t0))


if "gioco" in sys.argv:
    main()
