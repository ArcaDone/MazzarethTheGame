"""Palazzo Bartoli: everything that is not a street facade - staircase and loggia, carriage passage,
courtyard paving, gardens with hedges and trees, boundary walls with the gate, the strip on Via
Principe di Butera. Local metres, z above 169 m (see Lots/1249067196_layout.json).

Levels: courtyard 1.0, staircase landing 3.1, loggia and the first-floor gallery 5.7, tree garden 7.5,
hanging garden on the old body 6.1.
"""
import math
import os
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import m80_arch_facade as A
import m80_arch_kit as K

COURT = 1.0
LOGGIA = 5.9
GARDEN = 7.5
HANGING = 6.1


def part(name, p0, p1, z0, height=10.0):
    """A Facade frame used as a container for non-facade parts (high / low / detail collections)."""
    F = K.Facade(name, p0, p1, z0, height)
    return F


def both(F, name, fn, mat_hi, wear=1.0):
    """Build the same box-like part in high (weathered) and low."""
    M = A.mats()
    bm = bmesh.new()
    fn(bm)
    hi = K.bm_object(name + "_hi", bm, F.high, F.frame, mat_hi)
    bm = bmesh.new()
    fn(bm)
    K.bm_object(name, bm, F.low, F.frame, M["low"])
    if wear:
        K.densify(hi, 0.08)
        K.weather(hi, wear=wear, bevel=0.012, subdiv=1)
    return hi


# ---------------------------------------------------------------------------------------------
# Staircase "a tenaglia" and loggia (front line from the courtyard's west wall to the north wing)

def staircase_loggia():
    M = A.mats()
    F = part("Scalone", (-6.9, 5.9), (1.4, 8.6), COURT)
    W = F.width                      # ~8.7 m; frame: -Y = courtyard (south), +Y = garden (north)
    land = LOGGIA - COURT            # 4.7 above the courtyard
    mid = 2.1                        # central landing
    c0, c1 = W / 2 - 1.5, W / 2 + 1.5
    # Central flight: 14 steps from the courtyard to the landing.
    n = 14
    for k in range(n):
        y0 = -8.4 + 3.2 * k / n
        both(F, "Scalone_c%02d" % k, lambda bm, y0=y0, k=k: K.box_bm(bm, c0, c1, y0, -5.2, -0.3, mid * (k + 1) / n), M["stone"], 0.7)
    both(F, "Scalone_ripiano", lambda bm: K.box_bm(bm, 0.5, W - 0.5, -5.2, -4.0, -0.3, mid), M["stone"], 0.6)
    # Side flights up to the loggia, along the side walls.
    n2 = 17
    for side, (a, b) in (("s", (0.5, 2.0)), ("d", (W - 2.0, W - 0.5))):
        for k in range(n2):
            y0 = -4.0 + 4.0 * k / n2
            both(F, "Scalone_%s%02d" % (side, k), lambda bm, y0=y0, k=k, a=a, b=b: K.box_bm(bm, a, b, y0, 0.0, -0.3, mid + (land - mid) * (k + 1) / n2),
                 M["stone"], 0.7)
    # Between the side flights: terrace at the landing level, the loggia's retaining wall with a niche.
    both(F, "Scalone_terrazzino", lambda bm: K.box_bm(bm, 2.0, W - 2.0, -4.0, 0.0, -0.3, mid), M["stone"], 0.5)
    both(F, "Loggia_muro", lambda bm: K.box_bm(bm, 2.0, W - 2.0, -0.35, 0.0, mid, land), M["white"], 0.8)
    # Loggia floor and three arches on four piers, open to the sky (wisteria on top).
    both(F, "Loggia_pavimento", lambda bm: K.box_bm(bm, 0.5, W - 0.5, 0.0, 3.5, -0.3, land), M["stone"], 0.4)
    piers = [0.5 + (W - 1.0 - 0.55) * k / 3 for k in range(4)]
    for k, u in enumerate(piers):
        both(F, "Loggia_pilastro%d" % k, lambda bm, u=u: K.box_bm(bm, u, u + 0.55, 0.0, 0.55, land, land + 2.9), M["white"], 1.0)
    for k in range(3):
        a, b = piers[k] + 0.55, piers[k + 1]
        o = K.Opening(a, b, land, land + 2.9, (b - a) / 2)
        path = list(reversed(o.outline(16)))[1:-1]
        prof = [(0.0, 0.0), (0.0, -0.55), (0.45, -0.55), (0.45, 0.0)]   # through the pier depth (+Y)
        hi = K.sweep("Loggia_arco%d_hi" % k, path, prof, F.high, F.frame, M["white"])
        K.sweep("Loggia_arco%d" % k, path, prof, F.low, F.frame, M["low"])
        K.weather(hi, wear=1.0, bevel=0.0, subdiv=1)
    both(F, "Loggia_trabeazione", lambda bm: K.box_bm(bm, 0.4, W - 0.4, -0.05, 0.6, land + 2.9 + (piers[1] - piers[0] - 0.55) / 2 + 0.35,
                                                       land + 2.9 + (piers[1] - piers[0] - 0.55) / 2 + 0.75), M["white"], 0.9)
    # Stone balustrades along the central flight, starting from two pillars with urns; iron on the side
    # flights and the loggia.
    for u in (c0, c1):
        _balustrade_slope(F, "Scalone_balaustra_c%.0f" % u, u, -8.4, -5.2, 0.0, mid)
        both(F, "Scalone_pilastrino_c%.0f" % u, lambda bm, u=u: K.box_bm(bm, u - 0.19, u + 0.19, -8.62, -8.24, -0.3, 1.15), M["stone"], 0.6)
        urn(F, "Scalone_vaso_%.1f_pilastrino" % u, u, -8.43, 1.15, h=0.6)
    for u in (0.5, 2.0, W - 2.0, W - 0.5):
        _rail_slope(F, "Scalone_ringhiera_l%.1f" % u, u, -4.0, 0.0, mid, land)
    A.railing(F, "Loggia_ringhiera", 2.0, W - 2.0, -0.4, land, 1.0, "straight", sides=False)
    for (u, y, z) in ((0.6, -5.1, mid), (W - 0.6, -5.1, mid), (W / 2, -0.6, mid)):
        urn(F, "Scalone_vaso_%.1f_%.1f" % (u, y), u, y, z)
    wisteria(F, "Loggia_glicine", piers[0], piers[-1] + 0.55, land + 2.4, land + 5.3)
    return F


def _slope_prism(bm, u0, u1, y0, y1, za0, za1, zb0, zb1):
    """Prism between y0 and y1 whose bottom (za) and top (zb) follow the flight."""
    v = [bm.verts.new(c) for c in ((u0, y0, za0), (u1, y0, za0), (u1, y0, zb0), (u0, y0, zb0),
                                    (u0, y1, za1), (u1, y1, za1), (u1, y1, zb1), (u0, y1, zb1))]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)):
        bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def _balustrade_slope(F, name, u, y0, y1, z0, z1, h=0.95):
    """Stone balustrade along a flight: sloping plinth and coping, turned balusters (kept as real geometry)."""
    M = A.mats()
    plinth, coping = 0.16, 0.11
    both(F, name + "_zoccolo", lambda bm: _slope_prism(bm, u - 0.12, u + 0.12, y0, y1, z0 - 0.3, z1 - 0.3, z0 + plinth, z1 + plinth), M["stone"], 0.6)
    both(F, name + "_copertina", lambda bm: _slope_prism(bm, u - 0.15, u + 0.15, y0, y1, z0 + h - coping, z1 + h - coping, z0 + h, z1 + h),
         M["stone"], 0.8)
    # Baluster: base, belly low (a vase), neck, cap; heights as fractions of the free height.
    prof = [(0.075, 0.0), (0.075, 0.07), (0.055, 0.10), (0.06, 0.14), (0.085, 0.30), (0.08, 0.42), (0.05, 0.60),
            (0.035, 0.74), (0.05, 0.80), (0.045, 0.86), (0.07, 0.90), (0.07, 1.0)]
    free = h - plinth - coping
    bm = bmesh.new()
    seg = 12
    n = max(2, int(abs(y1 - y0) / 0.24))
    for k in range(n):
        t = (k + 0.5) / n
        y, zb = y0 + (y1 - y0) * t, z0 + (z1 - z0) * t + plinth
        rings = [[bm.verts.new((u + r * math.cos(2 * math.pi * j / seg), y + r * math.sin(2 * math.pi * j / seg), zb + f * free))
                  for j in range(seg)] for r, f in prof]
        for a, b in zip(rings[:-1], rings[1:]):
            for j in range(seg):
                bm.faces.new((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
    K.bm_object(name + "_colonnine", bm, F.detail, F.frame, M["stone"], smooth=True)


def _rail_slope(F, name, u, y0, y1, z0, z1, h=0.95):
    M = A.mats()
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.009
    n = max(2, int(abs(y1 - y0) / 0.12))
    for k in range(n + 1):
        t = k / n
        y, z = y0 + (y1 - y0) * t, z0 + (z1 - z0) * t
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (u, y, z, 1)
        sp.points[1].co = (u, y, z + h, 1)
    for dz in (0.05, h):
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (u, y0, z0 + dz, 1)
        sp.points[1].co = (u, y1, z1 + dz, 1)
    cu.materials.append(M["iron"])
    K.link(bpy.data.objects.new(name, cu), F.detail, F.frame)


def urn(F, name, u, y, z, h=0.75):
    """Terracotta urn with handles on a small pedestal (lathe profile)."""
    M = A.mats()
    prof = [(0.0, 0.0), (0.16, 0.0), (0.16, 0.30), (0.10, 0.34), (0.12, 0.40), (0.20, 0.52), (0.27, 0.70), (0.29, 0.86), (0.25, 0.98),
            (0.31, 1.04), (0.31, 1.10), (0.0, 1.10)]
    bm = bmesh.new()
    seg = 24
    rings = []
    for r, zz in prof:
        rings.append([bm.verts.new((u + r * math.cos(2 * math.pi * j / seg), y + r * math.sin(2 * math.pi * j / seg), z + zz * h)) for j in range(seg)])
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(seg):
            bm.faces.new((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    m = bpy.data.materials.get("Terracotta") or A.principled("Terracotta", (0.42, 0.18, 0.08), 0.85)
    ob = K.bm_object(name, bm, F.detail, F.frame, m, smooth=True)
    return ob


def wisteria(F, name, u0, u1, v0, v1, seed=4):
    """Wisteria over the loggia: woody stems and drooping lilac clusters among leaves."""
    if not VERDE:
        mk = marker(name, ((u0 + u1) / 2, -0.3, v1), 1.0, tipo="glicine", u0=u0, u1=u1, v0=v0, v1=v1)
        mk.parent = F.frame
        return None
    rnd = random.Random(seed)
    leaf = A.mats()["ivy"]
    flower = bpy.data.materials.get("Glicine") or A.principled("Glicine", (0.30, 0.18, 0.50), 0.6)
    for mat, count, size, droop in ((leaf, 2600, 0.07, 0.0), (flower, 700, 0.05, 0.35)):
        bm = bmesh.new()
        for _ in range(count):
            u = rnd.uniform(u0, u1)
            y = rnd.uniform(-0.3, 0.9)
            v = rnd.uniform(v0, v1) - (rnd.random() * droop)
            s = size * rnd.uniform(0.7, 1.3)
            a = rnd.uniform(0, math.tau)
            c, d = math.cos(a) * s, math.sin(a) * s
            vs = [bm.verts.new((u + c, y, v + d)), bm.verts.new((u - d, y + s * 0.5, v + c)),
                  bm.verts.new((u - c, y, v - d)), bm.verts.new((u + d, y - s * 0.5, v - c))]
            bm.faces.new(vs)
        K.bm_object(name + ("_foglie" if mat is leaf else "_fiori"), bm, F.detail, F.frame, mat)


# ---------------------------------------------------------------------------------------------
# Carriage passage ("androne") from the green gate on the Corso to the courtyard

def androne(gate_world, court_world, width=3.0, spring=3.2):
    M = A.mats()
    a, b = Vector(gate_world), Vector(court_world)
    F = part("Androne", (a.x, a.y), (b.x, b.y), 0.9)
    L = F.width
    # In this frame u runs from the gate to the courtyard; the passage spans y in [-w/2, w/2].
    hw = width / 2
    both(F, "Androne_pavimento", lambda bm: K.box_bm(bm, 0.0, L, -hw, hw, -0.3, 0.05), M["lava"], 0.5)
    for s in (-1, 1):
        both(F, "Androne_zoccolo%d" % s, lambda bm, s=s: K.box_bm(bm, 0.0, L, s * hw - (0.08 if s > 0 else 0), s * hw + (0.08 if s < 0 else 0), 0.0, 0.9),
             M["stone"], 0.8)
    plaster = bpy.data.materials.get("Intonaco_androne") or A.principled("Intonaco_androne", (0.42, 0.37, 0.28), 0.95)
    bm = bmesh.new()
    seg = 18
    for s in (-1, 1):
        v = [bm.verts.new(p) for p in ((0, s * hw, 0), (L, s * hw, 0), (L, s * hw, spring), (0, s * hw, spring))]
        bm.faces.new(v)
    ring0 = [bm.verts.new((0.0, -hw * math.cos(math.pi * j / seg), spring + hw * math.sin(math.pi * j / seg))) for j in range(seg + 1)]
    ring1 = [bm.verts.new((L, -hw * math.cos(math.pi * j / seg), spring + hw * math.sin(math.pi * j / seg))) for j in range(seg + 1)]
    for j in range(seg):
        bm.faces.new((ring0[j], ring0[j + 1], ring1[j + 1], ring1[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.dot(Vector((0, -c.y, spring - c.z if c.z > spring else 0))) < 0:
            f.normal_flip()
    hi = K.bm_object("Androne_volta_hi", bm, F.high, F.frame, plaster)
    bm2 = bmesh.new()
    bm2.from_mesh(hi.data)
    K.bm_object("Androne_volta", bm2, F.low, F.frame, M["low"])
    K.densify(hi, 0.1)
    K.weather(hi, wear=0.5, bevel=0.0, subdiv=1)
    # A lantern hanging from the vault.
    bm = bmesh.new()
    K.box_bm(bm, L / 2 - 0.15, L / 2 + 0.15, -0.15, 0.15, spring + hw - 1.6, spring + hw - 1.15)
    K.box_bm(bm, L / 2 - 0.01, L / 2 + 0.01, -0.01, 0.01, spring + hw - 1.15, spring + hw)
    K.bm_object("Androne_lanterna", bm, F.detail, F.frame, M["iron"])
    return F


# ---------------------------------------------------------------------------------------------
# Paving and gardens

def setts(U, V, seed=3):
    """Lava setts ("basolato"): rows of rectangular stones, dark, worn smooth, weeds in the joints."""
    h, alb = A.ashlar(U, V, course=0.24, length=0.42, seed=seed)
    alb = np.ones_like(alb) * np.array([0.055, 0.052, 0.05]) * (0.8 + 0.4 * K.value_noise(U, V, 0.15, seed + 1, 3))[..., None]
    joints = h < 0.001
    weeds = joints & (K.value_noise(U, V, 0.5, seed + 2, 3) > 0.55)
    alb = np.where(weeds[..., None], np.array([0.06, 0.10, 0.03]), alb)
    return h * 0.8, alb


def point_in_poly(x, y, poly):
    inside = np.zeros(np.shape(x), bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / ((y2 - y1) + 1e-12) + x1)
        inside ^= cond
    return inside


def ground_patch(name, poly, level, kind, col_high, col_low, step=0.03, px=80):
    """A horizontal surface over a polygon: 'setts' (displaced, high-poly) or flat for lawn/gravel."""
    M = A.mats()
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    nu, nv = int((x1 - x0) / step) + 2, int((y1 - y0) / step) + 2
    U, V = np.meshgrid(np.linspace(x0, x1, nu), np.linspace(y0, y1, nv))
    if kind == "setts":
        h, alb = setts(U, V)
    elif kind == "gravel":
        h = 0.01 * K.value_noise(U, V, 0.03, 5, 3)
        alb = np.array([0.42, 0.36, 0.27]) * (0.8 + 0.35 * K.value_noise(U, V, 0.02, 6, 3))[..., None]
    elif kind == "lawn" and VERDE:
        h = 0.02 * K.value_noise(U, V, 0.2, 7, 3)
        alb = np.array([0.07, 0.13, 0.035]) * (0.7 + 0.6 * K.value_noise(U, V, 0.15, 8, 4))[..., None]
    else:
        # Bare soil where Unreal will put the grass.
        h = 0.02 * K.value_noise(U, V, 0.2, 7, 3)
        alb = np.array([0.16, 0.11, 0.07]) * (0.75 + 0.5 * K.value_noise(U, V, 0.1, 8, 4))[..., None]
    co = np.stack([U, V, level + h], -1).reshape(-1, 3)
    cu = (U[:-1, :-1] + U[1:, 1:]) / 2
    cv = (V[:-1, :-1] + V[1:, 1:]) / 2
    keep = point_in_poly(cu, cv, poly).reshape(-1)
    ii, jj = np.meshgrid(np.arange(nu - 1), np.arange(nv - 1))
    a = (jj * nu + ii).reshape(-1)
    quads = np.stack([a, a + 1, a + 1 + nu, a + nu], -1)[keep]
    me = bpy.data.meshes.new(name + "_hi")
    me.vertices.add(len(co))
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set("vertex_index", quads.astype(np.int32).ravel())
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", (np.arange(len(quads)) * 4).astype(np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(quads), 4, np.int32))
    uv = me.uv_layers.new(name="UVMap")
    lu = ((co[quads.ravel(), 0] - x0) / (x1 - x0)).astype(np.float32)
    lv = ((co[quads.ravel(), 1] - y0) / (y1 - y0)).astype(np.float32)
    uv.data.foreach_set("uv", np.stack([lu, lv], -1).ravel())
    me.update(calc_edges=True)
    hi = bpy.data.objects.new(name + "_hi", me)
    col_high.objects.link(hi)
    img = K.image_from_array(name + "_albedo", ((np.clip(alb, 0, 1)) ** (1 / 2.2)).astype(np.float32))
    mat = bpy.data.materials.new(name + "_hi")
    mat.use_nodes = True
    t = mat.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = img
    mat.node_tree.links.new(t.outputs[0], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.7 if kind == "setts" else 0.95
    me.materials.append(mat)
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, level)) for x, y in poly]
    bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me2 = bpy.data.meshes.new(name)
    bm.to_mesh(me2)
    bm.free()
    lo = bpy.data.objects.new(name, me2)
    me2.materials.append(M["low"])
    col_low.objects.link(lo)
    return hi, lo


def hedge_rect(bm, x0, y0, x1, y1, z, w=0.32, h=0.5):
    for a, b in (((x0, y0), (x1, y0 + w)), ((x0, y1 - w), (x1, y1)), ((x0, y0), (x0 + w, y1)), ((x1 - w, y0), (x1, y1))):
        K.box_bm(bm, a[0], b[0], a[1], b[1], z, z + h)


def box_hedges(name, beds, z, col):
    """Clipped box hedges: boxes, then rounded and made leafy by subdivision and a noise displacement."""
    if not VERDE:
        for k, (x0, y0, x1, y1) in enumerate(beds):
            marker("%s_%d" % (name, k), ((x0 + x1) / 2, (y0 + y1) / 2, z), 0.5, tipo="siepe_bosso",
                   rettangolo=[x0, y0, x1, y1], altezza_m=0.55, spessore_m=0.4)
        return None
    bm = bmesh.new()
    for x0, y0, x1, y1 in beds:
        hedge_rect(bm, x0, y0, x1, y1, z)
    m = bpy.data.materials.get("Bosso") or A.principled("Bosso", (0.03, 0.075, 0.02), 0.8)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    me.materials.append(m)
    col.objects.link(ob)
    K.densify(ob, 0.1)
    s = ob.modifiers.new("Sub", "SUBSURF")
    s.levels = s.render_levels = 1
    tex = bpy.data.textures.get("M80_Foglie") or bpy.data.textures.new("M80_Foglie", "CLOUDS")
    tex.noise_scale = 0.05
    d = ob.modifiers.new("Foglie", "DISPLACE")
    d.texture = tex
    d.strength = 0.06
    d.texture_coords = "GLOBAL"
    return ob


# Greenery (trees, hedges, lawns, wisteria) is planted in Unreal: here only markers (empties) with the
# planned sizes, exported with the model. M80_VERDE=1 brings back the Blender placeholders for a look.
VERDE = os.environ.get("M80_VERDE", "0") == "1"


def marker(name, loc, size, **props):
    mk = bpy.data.objects.new(name, None)
    mk.empty_display_type = "CONE"
    mk.empty_display_size = max(size, 0.2)
    mk.location = loc
    for k, v in props.items():
        mk[k] = v
    K.collection("Vegetazione_Marker").objects.link(mk)
    return mk


def tree(name, x, y, z, height, crown, col, kind="broad", seed=1):
    """Trees are planted in Unreal with real foliage: here only a marker (empty) with the planned size,
    exported with the model so the trees can be placed at the same spots (see VERDE)."""
    if not VERDE:
        return marker(name, (x, y, z), crown / 2, altezza_m=height, chioma_m=crown, tipo=kind)
    rnd = random.Random(seed)
    bark = bpy.data.materials.get("Corteccia") or A.principled("Corteccia", (0.06, 0.045, 0.03), 0.9)
    leaves = bpy.data.materials.get("Chioma") or A.principled("Chioma", (0.03, 0.08, 0.02), 0.8)
    bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=0.12 + 0.02 * height, radius2=0.05, depth=height * 0.75,
                                    location=(x, y, z + height * 0.375))
    trunk = bpy.context.object
    trunk.name = name + "_tronco"
    trunk.data.materials.append(bark)
    _move(trunk, col)
    for k in range(9 if kind == "broad" else 5):
        if kind == "cypress":
            cx, cy, cz, r = x, y, z + height * (0.35 + 0.08 * k), crown * (1 - 0.15 * k) * 0.5
        else:
            cx = x + rnd.uniform(-crown, crown) * 0.5
            cy = y + rnd.uniform(-crown, crown) * 0.5
            cz = z + height * rnd.uniform(0.62, 0.9)
            r = crown * rnd.uniform(0.35, 0.6)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=max(0.3, r), location=(cx, cy, cz))
        c = bpy.context.object
        c.name = "%s_chioma%d" % (name, k)
        if kind == "cypress":
            c.scale = (1, 1, 1.8)
        c.data.materials.append(leaves)
        tex = bpy.data.textures.get("M80_Chioma") or bpy.data.textures.new("M80_Chioma", "CLOUDS")
        tex.noise_scale = 0.35
        d = c.modifiers.new("Foglie", "DISPLACE")
        d.texture = tex
        d.strength = 0.5
        d.texture_coords = "GLOBAL"
        c.data.shade_smooth()
        _move(c, col)


def _move(ob, col):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    col.objects.link(ob)


def fountain(name, x, y, z, col):
    m = A.mats()["white"]
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=1.3, depth=0.55, location=(x, y, z + 0.27))
    b = bpy.context.object
    b.name = name + "_vasca"
    b.data.materials.append(m)
    _move(b, col)
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=1.15, depth=0.05, location=(x, y, z + 0.45))
    w = bpy.context.object
    w.name = name + "_acqua"
    w.data.materials.append(bpy.data.materials.get("Acqua") or A.principled("Acqua", (0.02, 0.05, 0.05), 0.02))
    _move(w, col)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.14, depth=1.1, location=(x, y, z + 0.8))
    p = bpy.context.object
    p.name = name + "_colonnina"
    p.data.materials.append(m)
    _move(p, col)


def gardens(layout, ground_fn):
    col_hi = K.collection("Giardini_High")
    col_lo = K.collection("Giardini_Low")
    col_d = K.collection("Giardini_Detail")
    g1 = layout["giardino_alberi"]["poly"]
    ground_patch("Giardino_ghiaia", g1, GARDEN, "gravel", col_hi, col_lo)
    # Italian garden of the tree garden: four beds bordered by box hedges around a fountain.
    cx, cy = -14.0, 9.5
    beds = []
    for dx in (-1, 1):
        for dy in (-1, 1):
            x0 = cx + (0.8 if dx > 0 else -6.3)
            y0 = cy + (0.8 if dy > 0 else -5.3)
            beds.append((x0, y0, x0 + 5.5, y0 + 4.5))
    box_hedges("Giardino_bosso", beds, GARDEN, col_d)
    for k, (x0, y0, x1, y1) in enumerate(beds):
        ground_patch("Giardino_aiuola%d" % k, [(x0 + 0.3, y0 + 0.3), (x1 - 0.3, y0 + 0.3), (x1 - 0.3, y1 - 0.3), (x0 + 0.3, y1 - 0.3)],
                     GARDEN + 0.03, "lawn", col_hi, col_lo, step=0.06)
    fountain("Giardino_fontana", cx, cy, GARDEN, col_d)
    for k, (x, y, h, c, kind) in enumerate(((-5.5, 15.5, 11.0, 7.0, "broad"), (-22.0, 16.0, 9.0, 6.0, "broad"), (-25.5, 3.0, 8.0, 1.6, "cypress"),
                                            (-19.0, 3.5, 4.0, 2.5, "broad"))):
        tree("Albero_g1_%d" % k, x, y, GARDEN, h, c, col_d, kind, seed=k + 1)
    # Hanging garden on the old body.
    b = layout["bodies"]["B_corpo_antico"]["poly"]
    ground_patch("Pensile_ghiaia", b, HANGING, "gravel", col_hi, col_lo, step=0.05)
    beds = []
    for i in range(3):
        for j in range(4):
            x0 = -33.0 + 5.2 * i + (j * 1.3)
            y0 = -31.5 + 5.6 * j
            beds.append((x0, y0, x0 + 3.6, y0 + 3.8))
    beds = [bd for bd in beds if point_in_poly(np.array([(bd[0] + bd[2]) / 2]), np.array([(bd[1] + bd[3]) / 2]), b)[0]]
    box_hedges("Pensile_bosso", beds, HANGING, col_d)
    for k, (x0, y0, x1, y1) in enumerate(beds):
        if k % 3 == 1:
            tree("Agrume_%d" % k, (x0 + x1) / 2, (y0 + y1) / 2, HANGING, 2.6, 1.6, col_d, "broad", seed=40 + k)
    # North-east garden: lawn on the slope and trees.
    g2 = layout["giardino_nordest"]["poly"]
    zs = [ground_fn(x, y) for x, y in g2]
    ground_patch("GiardinoNE_prato", g2, min(zs) + 0.4, "lawn", col_hi, col_lo, step=0.08)
    for k, (x, y, h, c) in enumerate(((25.0, 26.0, 10.0, 6.5), (24.0, 16.0, 8.0, 5.0), (29.5, 13.0, 9.0, 5.5), (31.0, 6.5, 6.0, 4.0))):
        tree("Albero_ne_%d" % k, x, y, ground_fn(x, y), h, c, col_d, "broad", seed=20 + k)


# ---------------------------------------------------------------------------------------------
# Boundary walls on Piazza Monterosso and Via Principe di Butera (with the gate), and the strip N

def wall_specs(ground_fn):
    specs = []
    # Straight on from the facade of D on the piazza to the corner on Via Principe di Butera, then to the house.
    pts = [(37.0, 3.8), (25.8, 34.7), (18.6, 33.4)]
    for k in range(len(pts) - 1):
        p0, p1 = pts[k], pts[k + 1]
        L = math.dist(p0, p1)
        g = [ground_fn(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t) for t in np.linspace(0, 1, 9)]
        z0 = min(g) - 0.2
        top = [[L * t, gg - z0 + 3.8] for t, gg in zip(np.linspace(0, 1, 9), g)]
        spec = {"name": "Muro_cinta%d" % k, "p0": list(p0), "p1": list(p1), "z0": z0, "height": max(t[1] for t in top) + 0.1,
                "wall": {"type": "rubble", "seed": 50 + k}, "openings": [], "top": top}
        specs.append(spec)
    return specs


def facade_n(ground_fn):
    p0, p1 = (1.5, 38.75), (-38.3, 26.8)
    g = [ground_fn(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t) for t in np.linspace(0, 1, 9)]
    z0 = min(g) - 0.2
    L = math.dist(p0, p1)
    o = []
    for k, u in enumerate(np.linspace(3.0, L - 3.0, 9)):
        gl = np.interp(u, np.linspace(0, L, 9), g) - z0
        if k % 3 == 1:
            o.append({"id": "N_T%d" % k, "u0": u - 0.6, "u1": u + 0.6, "v0": gl, "v1": gl + 2.4, "kind": "door", "fit": "door", "door_mat": "green"})
        else:
            o.append({"id": "N_F%d" % k, "u0": u - 0.5, "u1": u + 0.5, "v0": gl + 1.2, "v1": gl + 2.5, "kind": "window", "fit": "grille", "sill": True})
        o.append({"id": "N_P%d" % k, "u0": u - 0.5, "u1": u + 0.5, "v0": gl + 4.3, "v1": gl + 5.9, "kind": "window", "fit": "shutters", "sill": True})
    return {"name": "N_Butera", "p0": list(p0), "p1": list(p1), "z0": z0, "height": max(g) - z0 + 7.6,
            "wall": {"type": "plaster", "color": (0.60, 0.53, 0.42), "peel": 0.5, "seed": 61}, "openings": o,
            "top": [[L * t, gg - z0 + 7.2] for t, gg in zip(np.linspace(0, 1, 9), g)]}
