"""Facades from data (Mazzarino 80): one dict per facade -> high-poly, low-poly and fittings.

Spec keys (metres, facade frame: u along from p0, v up from z0, outside is -Y):
  name, p0, p1, z0, height
  wall: {"type": "rubble" | "ashlar" | "plaster", "color": (r, g, b) for plaster, "peel": 0..1,
         "course": ashlar course height, "seed": int}
  openings: list of {id, u0, u1, v0, v1, arch, kind, fit, frame, sill, keystone, lunette, aedicule}
     kind: window | french | door | portal | arch_door | shop | open_arch | empty
     fit:  shutters | shutters_open | glazed | grille | door | portal | shop | roll | rail | none
     frame: None or {"w": .16, "proj": .055, "mat": "stone" | "portal"}
  balconies: list of {u0, u1, v, d, brackets: "simple" | "rich", n, railing: "straight" | "bombe"}
  pilasters: list of [u0, u1, proj, "quoin" | ""]
  bands: list of {"v", "profile": "string" | "cornice" | "plinth", "u0", "u1"}
  cornice: {"v", "tiles": bool, "profile": "cornice" | "string"}
  anchors: [[u, v]], plaques: [[u0, u1, v0, v1]]
  ruin: {"u0", "u1", "top": v} ragged top of a roofless stretch; ivy: [[u0, u1, v0, v1]]
"""
import math
import os
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import m80_arch_kit as K


# ---------------------------------------------------------------------------------------------
# Materials (linear colours)

_M = {}
# Wall albedo into its sRGB image: exponent (1/2.2, the sRGB encoding; M80_WALL_GAMMA=1 gives back the darker walls of
# the first previews) and saturation (M80_WALL_SAT, 1 = as generated).
WALL_GAMMA = float(os.environ.get("M80_WALL_GAMMA", str(1 / 2.2)))
WALL_SAT = float(os.environ.get("M80_WALL_SAT", "0.75"))


def principled(name, color, rough=0.85, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def stone_material(name, base, dark, scale=6.0, pitting=0.35):
    """High-poly stone: mottled colour, dirt in hollows, worn pale edges, lichen; pitting bump."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = scale
    n1.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*base, 1)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.7
    nt.links.new(n1.outputs["Fac"], ramp.inputs[0])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    wear = nt.nodes.new("ShaderNodeValToRGB")
    e = wear.color_ramp.elements
    e[0].position, e[0].color = 0.44, (0.55, 0.50, 0.44, 1)
    e[1].position, e[1].color = 0.56, (1.18, 1.14, 1.08, 1)
    wear.color_ramp.elements.new(0.5).color = (1, 1, 1, 1)
    nt.links.new(geo.outputs["Pointiness"], wear.inputs[0])
    dirt = nt.nodes.new("ShaderNodeMix")
    dirt.data_type = "RGBA"
    dirt.blend_type = "MULTIPLY"
    dirt.inputs["Factor"].default_value = 1.0
    nt.links.new(ramp.outputs[0], dirt.inputs[6])
    nt.links.new(wear.outputs[0], dirt.inputs[7])
    lich = nt.nodes.new("ShaderNodeTexNoise")
    lich.inputs["Scale"].default_value = 2.5
    lich.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], lich.inputs["Vector"])
    lr = nt.nodes.new("ShaderNodeMapRange")
    lr.inputs["From Min"].default_value = 0.62
    lr.inputs["From Max"].default_value = 0.70
    nt.links.new(lich.outputs["Fac"], lr.inputs["Value"])
    lm = nt.nodes.new("ShaderNodeMix")
    lm.data_type = "RGBA"
    nt.links.new(lr.outputs[0], lm.inputs["Factor"])
    nt.links.new(dirt.outputs[2], lm.inputs[6])
    lm.inputs[7].default_value = (0.20, 0.21, 0.15, 1)
    nt.links.new(lm.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.88
    pit = nt.nodes.new("ShaderNodeTexVoronoi")
    pit.inputs["Scale"].default_value = 90
    nt.links.new(tc.outputs["Object"], pit.inputs["Vector"])
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 140
    fine.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(pit.outputs["Distance"], add.inputs[0])
    nt.links.new(fine.outputs["Fac"], add.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = pitting
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(add.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    return m


def mats():
    if _M:
        return _M
    _M.update({
        "stone": stone_material("Arenaria_hi", (0.46, 0.34, 0.19), (0.33, 0.23, 0.12)),
        "portal": stone_material("Arenaria_portale_hi", (0.48, 0.26, 0.09), (0.32, 0.16, 0.05), pitting=0.45),
        "white": stone_material("Pietra_bianca_hi", (0.62, 0.58, 0.50), (0.48, 0.44, 0.38), pitting=0.25),
        "lava": stone_material("Pietra_lavica_hi", (0.07, 0.07, 0.07), (0.035, 0.035, 0.035), pitting=0.6),
        "yellow": stone_material("Intonaco_giallo_hi", (0.55, 0.38, 0.10), (0.44, 0.29, 0.07), pitting=0.15),
        "marble": stone_material("Marmo_hi", (0.75, 0.74, 0.70), (0.62, 0.61, 0.58), scale=3, pitting=0.08),
        "low": principled("Cotto_facciata", (0.5, 0.4, 0.3)),
        "iron": principled("Ferro", (0.035, 0.035, 0.035), 0.55, 0.7),
        "green": principled("Persiane_verdi", (0.018, 0.048, 0.034), 0.55),
        "wood": principled("Legno_portone", (0.042, 0.018, 0.007), 0.62),
        "wood_light": principled("Legno_chiaro", (0.11, 0.055, 0.025), 0.6),
        "frame": principled("Telai", (0.22, 0.20, 0.17), 0.6),
        "glass": principled("Vetro", (0.02, 0.025, 0.03), 0.05),
        "brass": principled("Ottone", (0.55, 0.42, 0.18), 0.35, 1.0),
        "coppi": principled("Coppi", (0.34, 0.14, 0.08), 0.8),
        "roll": principled("Serranda", (0.16, 0.16, 0.15), 0.5, 0.6),
        "sign": principled("Insegna", (0.55, 0.50, 0.38), 0.6),
        "ivy": principled("Edera", (0.025, 0.06, 0.018), 0.6),
        "dark": principled("Interno_buio", (0.03, 0.025, 0.02), 0.9),
    })
    return _M


# ---------------------------------------------------------------------------------------------
# Wall surfaces: height (m, outward) and linear albedo

def ashlar(U, V, course=0.33, length=0.62, seed=3):
    row = np.floor(V / course).astype(np.int64)
    off = K._hash(row, row * 0 + 7, seed) * length
    col = np.floor((U + off) / length).astype(np.int64)
    lu = (U + off) - col * length
    lv = V - row * course
    edge = np.minimum(np.minimum(lu, length - lu), np.minimum(lv, course - lv))
    rnd = K._hash(col, row, seed + 1)
    joint = 0.006 + 0.003 * K.value_noise(U, V, 0.3, seed + 2, 2)
    face = np.clip((edge - joint) / 0.035, 0, 1) ** 0.5
    fine = K.value_noise(U, V, 0.02, seed + 4, 3)
    # Alveolar erosion of the sandstone: pitted, darker patches eaten into some blocks.
    erosion = np.clip((K.value_noise(U, V, 0.45, seed + 7, 3) - 0.6) * 4.0, 0, 1) * face
    pits = K.value_noise(U, V, 0.012, seed + 8, 2)
    h = np.where(edge < joint, 0.0, 0.006 + 0.004 * face + 0.003 * rnd + 0.002 * fine * face - 0.005 * erosion * pits)
    base = np.array([0.46, 0.36, 0.20])
    col_ = base * (0.80 + 0.32 * rnd)[..., None] * (0.85 + 0.22 * K.value_noise(U, V, 0.08, seed + 5, 3))[..., None]
    col_ = col_ * (1 - 0.28 * erosion * (0.6 + 0.4 * pits))[..., None]
    mortar = np.array([0.52, 0.44, 0.31])
    alb = np.where((edge < joint)[..., None], mortar, col_)
    return h, alb


def plaster(U, V, color, peel=0.3, seed=5):
    n = K.value_noise(U, V, 0.5, seed, 4)
    h = 0.014 + 0.003 * n
    alb = np.array(color) * (0.86 + 0.2 * K.value_noise(U, V, 0.9, seed + 1, 4))[..., None]
    # Stains and grime.
    alb = alb * (1 - 0.18 * np.clip(K.value_noise(U, V, 2.5, seed + 2, 3) - 0.45, 0, 1)[..., None] * 2)
    if peel > 0:
        mask = (K.value_noise(U, V, 1.5, seed + 3, 4) + 0.25 * np.clip(1 - V / 2.0, 0, 1)) > (0.78 - 0.25 * peel)
        rh, sid, edge = K.rubble(U, V, seed=seed + 9)
        ralb = K.rubble_albedo(U, V, rh, sid, edge, seed=seed + 9)
        h = np.where(mask, rh * 0.8, h)
        alb = np.where(mask[..., None], ralb, alb)
    return h, alb


def surface(spec, U, V):
    w = spec.get("wall", {"type": "rubble"})
    t = w.get("type", "rubble")
    if t == "ashlar":
        return ashlar(U, V, w.get("course", 0.33), w.get("length", 0.62), w.get("seed", 3))
    if t == "plaster":
        return plaster(U, V, w.get("color", (0.62, 0.55, 0.42)), w.get("peel", 0.3), w.get("seed", 5))
    h, sid, edge = K.rubble(U, V, cell=tuple(w.get("cell", (0.21, 0.14))), seed=w.get("seed", 7), mortar=w.get("mortar", 0.016))
    return h, K.rubble_albedo(U, V, h, sid, edge, seed=w.get("seed", 7))


# ---------------------------------------------------------------------------------------------
# Fittings and stone elements

def extrude_outline(bm, outline, u0, u1, v_top):
    a = [bm.verts.new((u0, -o, v_top + d)) for o, d in outline]
    b = [bm.verts.new((u1, -o, v_top + d)) for o, d in outline]
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    n = len(outline)
    for i in range(n):
        bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))


def bracket_outline(depth, height, rich):
    """Side outline (out, down) of a console, from the wall along the underside of the slab it carries."""
    if not rich:
        pts = [(0.0, 0.0), (depth, 0.0), (depth, -0.07)]
        n = 12
        for k in range(1, n + 1):
            t = k / n
            out = depth * (1 - t) ** 1.4 + 0.04
            down = -0.07 - (height - 0.07) * (math.sin(t * math.pi / 2) ** 1.2)
            pts.append((out, down))
        pts.append((0.0, -height))
        return pts
    # Baroque console: a roll under the front of the slab, an S (cyma) curving back to the wall and a
    # smaller roll at the foot.
    r = min(0.075, height * 0.14)
    rf = r * 0.7
    pts = [(0.0, 0.0)]
    for k in range(13):
        a = math.radians(90 - 180 * k / 12)
        pts.append((depth - r + r * math.cos(a), -r + r * math.sin(a)))
    x0, z0 = depth - r, -2 * r
    x1, z1 = rf + 0.03, -height + 2 * rf
    for k in range(1, 15):
        t = k / 14
        c = 0.5 - 0.5 * math.cos(math.pi * t)
        pts.append((x0 + (x1 - x0) * c, z0 + (z1 - z0) * t))
    for k in range(1, 13):
        a = math.radians(90 - 180 * k / 12)
        pts.append((x1 + rf * math.cos(a), z1 - rf + rf * math.sin(a)))
    pts.append((0.0, -height))
    return pts


def balcony(F, name, b):
    M = mats()
    u0, u1, v_top, d = b["u0"], b["u1"], b["v"], b["d"]
    w = u1 - u0
    thick = b.get("thick", 0.14)
    rich = b.get("brackets", "simple") == "rich"
    for coll, mat, sfx in ((F.high, M[b.get("mat", "stone")], "_hi"), (F.low, M["low"], "")):
        bm = bmesh.new()
        K.box_bm(bm, u0, u1, -d, 0.0, v_top - thick, v_top)
        K.bm_object(name + "_soletta" + sfx, bm, coll, F.frame, mat)
    edge = K.profile_resample([(0.0, 0.0), (0.0, 0.03), ("arc", -0.035, 0.03, 0.035, 90, 0), (-0.07, 0.03), (-0.07, 0.0)], 6)
    K.sweep(name + "_toro_hi", [(u0 - 0.02, v_top - thick), (u1 + 0.02, v_top - thick)],
            [(s, t + d) for s, t in edge], F.high, F.frame, M[b.get("mat", "stone")], smooth=True)
    nb = b.get("n", 4 if rich else 3)
    bd = d - 0.06
    bh = b.get("bracket_h", 0.62 if rich else 0.48)
    for k in range(nb):
        uc = u0 + 0.25 + (w - 0.5) * k / max(1, nb - 1)
        for coll, mat, outline, sfx in ((F.high, M[b.get("mat", "stone")], bracket_outline(bd, bh, rich), "_hi"),
                                        (F.low, M["low"], bracket_outline(bd, bh, False)[::3] + [(0.0, -bh)], "")):
            bm = bmesh.new()
            half = 0.09 if rich else 0.08
            extrude_outline(bm, outline, uc - half, uc + half, v_top - thick)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            ob = K.bm_object("%s_mensola%d%s" % (name, k, sfx), bm, coll, F.frame, mat)
            if rich and sfx:
                carve(ob)
    railing(F, name + "_ringhiera", u0 + 0.05, u1 - 0.05, -d + 0.05, v_top, b.get("rail_h", 1.0),
            b.get("railing", "straight"))


def carve(ob, strength=0.018):
    """Carved stone (consoles, modillions): rounded edges and a chiselled, worn relief."""
    K.add_bevel(ob, 0.02, 3)
    s = ob.modifiers.new("Sub", "SUBSURF")
    s.levels = s.render_levels = 2
    tex = bpy.data.textures.get("M80_Intaglio") or bpy.data.textures.new("M80_Intaglio", "STUCCI")
    tex.noise_scale = 0.04
    d = ob.modifiers.new("Scolpito", "DISPLACE")
    d.texture = tex
    d.strength = strength
    d.texture_coords = "GLOBAL"


def modillions(F, name, u0, u1, v, mat, step):
    """Consoles under the corona of a cornice (cornice_profile laid at height v), one every step metres."""
    M = mats()
    n = max(1, int((u1 - u0) / step))
    for k in range(n):
        uc = u0 + (k + 0.5) * (u1 - u0) / n
        for coll, m, outline, sfx in ((F.high, mat, bracket_outline(0.36, 0.25, True), "_hi"),
                                      (F.low, M["low"], bracket_outline(0.36, 0.25, False)[::3] + [(0.0, -0.25)], "")):
            bm = bmesh.new()
            extrude_outline(bm, outline, uc - 0.07, uc + 0.07, v + 0.29)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            ob = K.bm_object("%s_modiglione%d%s" % (name, k, sfx), bm, coll, F.frame, m)
            if sfx:
                carve(ob, 0.012)


def railing(F, name, u0, u1, y_front, v0, h, style="straight", sides=True):
    """Wrought iron: square bars, flat rails, a band of C-scrolls; 'bombe' bulges out at the bottom."""
    M = mats()
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.008
    cu.bevel_resolution = 0
    # "bombe": the goose-breast railing of Sicilian balconies, bellied out in its lower half.
    bulge = 0.24 if style == "bombe" else 0.0

    def bar(pts, depth=None):
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, c in zip(sp.points, pts):
            p.co = (*c, 1)

    def front_y(z):
        t = (z - v0) / h
        return y_front - bulge * math.sin(math.pi * min(1.0, t * 1.4)) * (1 - t) ** 0.3

    n = max(2, int((u1 - u0) / 0.115))
    zs = [v0 + 0.03 + (h - 0.03) * k / 10 for k in range(11)]
    for k in range(n + 1):
        u = u0 + (u1 - u0) * k / n
        bar([(u, front_y(z), z) for z in zs])
    for z in (v0 + 0.03, v0 + 0.22, v0 + h):
        bar([(u0, front_y(z), z), (u1, front_y(z), z)])
    if sides:
        for u in (u0, u1):
            m = max(2, int(abs(y_front) / 0.115))
            for k in range(m):
                y = y_front * k / m
                bar([(u, y, v0 + 0.03), (u, y, v0 + h)])
            for z in (v0 + 0.03, v0 + h):
                bar([(u, 0.0, z), (u, front_y(z), z)])
    # Scroll bands: C-scrolls facing each other; the bellied railing has a second, smaller band at the top.
    bands = [(v0 + 0.125, 0.085)] + ([(v0 + h - 0.13, 0.06)] if bulge else [])
    for zc, r0 in bands:
        n2 = max(2, int((u1 - u0) / (r0 * 2.7)))
        if bulge:
            zb = zc - r0 - 0.012
            bar([(u0, front_y(zb), zb), (u1, front_y(zb), zb)])
        for k in range(n2):
            uc = u0 + (u1 - u0) * (k + 0.5) / n2
            pts = []
            for j in range(17):
                a = math.radians(-90 + j * 22.5)
                r = r0 * (1 - j / 26)
                z = zc + r * math.sin(a)
                pts.append((uc + r * math.cos(a) * (1 if k % 2 else -1), front_y(z), z))
            bar(pts)
    cu.materials.append(M["iron"])
    ob = bpy.data.objects.new(name, cu)
    K.link(ob, F.detail, F.frame)
    # Handrail: a rounded bar on top.
    hr = bpy.data.curves.new(name + "_corrimano", "CURVE")
    hr.dimensions = "3D"
    hr.bevel_depth = 0.02
    hr.bevel_resolution = 3
    sp = hr.splines.new("POLY")
    pts = [(u0 - 0.01, front_y(v0 + h), v0 + h + 0.012), (u1 + 0.01, front_y(v0 + h), v0 + h + 0.012)]
    if sides:
        pts = [(u0 - 0.01, 0.0, v0 + h + 0.012)] + pts + [(u1 + 0.01, 0.0, v0 + h + 0.012)]
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    hr.materials.append(M["iron"])
    K.link(bpy.data.objects.new(name + "_corrimano", hr), F.detail, F.frame)
    return ob


def louvred_leaf(bm, a, b, v0, top, y, open_angle=0.0):
    K.box_bm(bm, a, a + 0.06, y, y + 0.04, v0, top)
    K.box_bm(bm, b - 0.06, b, y, y + 0.04, v0, top)
    mid = (v0 + top) / 2
    for z0, z1 in ((v0, v0 + 0.12), (top - 0.08, top), (mid - 0.04, mid + 0.04)):
        K.box_bm(bm, a + 0.06, b - 0.06, y, y + 0.04, z0, z1)
    z = v0 + 0.14
    while z < top - 0.12:
        if abs(z - mid) > 0.06:
            v = [bm.verts.new(p) for p in ((a + 0.06, y + 0.035, z), (b - 0.06, y + 0.035, z),
                                           (b - 0.06, y + 0.005, z + 0.045), (a + 0.06, y + 0.005, z + 0.045))]
            bm.faces.new(v)
        z += 0.05


def shutters(F, name, o, closed=True, inset=0.06):
    M = mats()
    bm = bmesh.new()
    mid = (o.u0 + o.u1) / 2
    top = o.v1
    if closed:
        louvred_leaf(bm, o.u0 + 0.01, mid - 0.005, o.v0, top, inset)
        louvred_leaf(bm, mid + 0.005, o.u1 - 0.01, o.v0, top, inset)
    else:
        # Folded back against the wall on both sides of the opening.
        w = (o.u1 - o.u0) / 2
        louvred_leaf(bm, o.u0 - 0.17 - w, o.u0 - 0.17, o.v0, top, -0.06)
        louvred_leaf(bm, o.u1 + 0.17, o.u1 + 0.17 + w, o.v0, top, -0.06)
        glazed(F, name + "_vetrata", o, inset=0.16)
    return K.bm_object(name, bm, F.detail, F.frame, M["green"])


def glazed(F, name, o, inset=0.12, bars=False):
    M = mats()
    bm = bmesh.new()
    y = inset
    t = 0.055
    K.box_bm(bm, o.u0, o.u0 + t, y, y + 0.06, o.v0, o.v1)
    K.box_bm(bm, o.u1 - t, o.u1, y, y + 0.06, o.v0, o.v1)
    K.box_bm(bm, o.u0, o.u1, y, y + 0.06, o.v0, o.v0 + t)
    K.box_bm(bm, o.u0, o.u1, y, y + 0.06, o.v1 - t, o.v1)
    mid = (o.u0 + o.u1) / 2
    K.box_bm(bm, mid - 0.025, mid + 0.025, y, y + 0.06, o.v0, o.v1)
    tr = o.v0 + (o.v1 - o.v0) * 0.68
    K.box_bm(bm, o.u0, o.u1, y, y + 0.06, tr - 0.02, tr + 0.02)
    K.bm_object(name + "_telaio", bm, F.detail, F.frame, M["frame"])
    bm = bmesh.new()
    pts = o.outline(16)
    vs = [bm.verts.new((u, y + 0.03, v)) for u, v in pts]
    bm.faces.new(vs)
    K.bm_object(name + "_vetro", bm, F.detail, F.frame, M["glass"])
    if bars:
        grille(F, name + "_grata", o, 0.03)


def grille(F, name, o, y=0.03):
    M = mats()
    bm = bmesh.new()
    n = max(2, int((o.u1 - o.u0) / 0.12))
    for k in range(1, n):
        u = o.u0 + (o.u1 - o.u0) * k / n
        K.box_bm(bm, u - 0.009, u + 0.009, y, y + 0.02, o.v0, o.top)
    for z in (o.v0 + 0.3, o.top - 0.3):
        K.box_bm(bm, o.u0, o.u1, y - 0.005, y + 0.025, z - 0.015, z + 0.015)
    K.bm_object(name, bm, F.detail, F.frame, M["iron"])


def lunette(F, name, o, y=0.12):
    """Fan grille ("raggiera") in the arch above the door's spring line, with a medallion."""
    M = mats()
    if o.arch <= 0:
        return
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.01
    half = (o.u1 - o.u0) / 2
    r = (half * half + o.arch * o.arch) / (2 * o.arch)
    c = ((o.u0 + o.u1) / 2, o.v1 + o.arch - r)
    a0 = math.atan2(o.v1 - c[1], half)
    for k in range(9):
        a = a0 + (math.pi - 2 * a0) * k / 8
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (c[0] + 0.15 * math.cos(a), y, max(o.v1, c[1] + 0.15 * math.sin(a)), 1)
        sp.points[1].co = (c[0] + r * math.cos(a), y, c[1] + r * math.sin(a), 1)
    for rr in (0.15, r * 0.6, r):
        sp = cu.splines.new("POLY")
        pts = [(c[0] + rr * math.cos(a0 + (math.pi - 2 * a0) * j / 16), y, max(o.v1, c[1] + rr * math.sin(a0 + (math.pi - 2 * a0) * j / 16))) for j in range(17)]
        sp.points.add(len(pts) - 1)
        for p, q in zip(sp.points, pts):
            p.co = (*q, 1)
    sp = cu.splines.new("POLY")
    sp.points.add(1)
    sp.points[0].co = (o.u0, y, o.v1, 1)
    sp.points[1].co = (o.u1, y, o.v1, 1)
    cu.materials.append(M["iron"])
    ob = bpy.data.objects.new(name, cu)
    K.link(ob, F.detail, F.frame)


def door(F, name, o, mat, inset=0.25, leaves=2, rows=3, knockers=False, to_v1=False):
    """Panelled door; to_v1 stops it at the spring line (a lunette above)."""
    M = mats()
    top = o.v1 if to_v1 else None
    pts = o.outline(24) if top is None else [(o.u1, o.v0), (o.u1, o.v1), (o.u0, o.v1), (o.u0, o.v0)]
    bm = bmesh.new()
    a = [bm.verts.new((u, inset, v)) for u, v in pts]
    b = [bm.verts.new((u, inset + 0.07, v)) for u, v in pts]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        bm.faces.new((a[i], b[i], b[(i + 1) % n], a[(i + 1) % n]))
    w = (o.u1 - o.u0) / leaves
    for L in range(leaves):
        x0 = o.u0 + L * w
        for r in range(rows):
            z0 = o.v0 + 0.15 + (o.v1 - 0.25 - o.v0) * r / rows
            z1 = o.v0 + 0.15 + (o.v1 - 0.25 - o.v0) * (r + 1) / rows - 0.12
            K.box_bm(bm, x0 + 0.1, x0 + w - 0.1, inset - 0.035, inset, z0, z1)
        if L < leaves - 1:
            K.box_bm(bm, x0 + w - 0.012, x0 + w + 0.012, inset - 0.04, inset, o.v0, o.v1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    K.bm_object(name, bm, F.detail, F.frame, mat)
    if knockers:
        mid = (o.u0 + o.u1) / 2
        for du in (-0.25, 0.25):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.07, minor_radius=0.012, major_segments=24, minor_segments=8)
            ring = bpy.context.object
            ring.name = name + "_anello"
            ring.data.materials.append(M["brass"])
            for c in list(ring.users_collection):
                c.objects.unlink(ring)
            K.link(ring, F.detail, F.frame)
            ring.rotation_euler = (math.pi / 2, 0, 0)
            ring.location = (mid + du, inset - 0.05, o.v0 + 1.25)


def roll_shutter(F, name, o, inset=0.10):
    M = mats()
    bm = bmesh.new()
    top = o.v1
    z = o.v0
    while z < top:
        K.box_bm(bm, o.u0, o.u1, inset, inset + 0.012, z, min(top, z + 0.07))
        K.box_bm(bm, o.u0, o.u1, inset - 0.006, inset, z + 0.03, min(top, z + 0.045))
        z += 0.075
    K.bm_object(name, bm, F.detail, F.frame, M["roll"])


def shop_front(F, name, o, inset=0.18):
    """1980s village shop: varnished wooden frame, glass door in the middle, shop windows, transom,
    a painted sign board above the opening."""
    M = mats()
    bm = bmesh.new()
    w = o.u1 - o.u0
    for u in (o.u0, o.u0 + w * 0.3, o.u0 + w * 0.7 - 0.06, o.u1 - 0.07):
        K.box_bm(bm, u, u + 0.07, inset, inset + 0.08, o.v0, o.v1)
    for z in (o.v0, o.v0 + 0.55, o.v1 - 0.55, o.v1 - 0.07):
        K.box_bm(bm, o.u0, o.u1, inset, inset + 0.08, z, z + 0.07)
    K.bm_object(name + "_telaio", bm, F.detail, F.frame, M["wood_light"])
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((o.u0, inset + 0.04, o.v0), (o.u1, inset + 0.04, o.v0), (o.u1, inset + 0.04, o.v1), (o.u0, inset + 0.04, o.v1))]
    bm.faces.new(vs)
    K.bm_object(name + "_vetro", bm, F.detail, F.frame, M["glass"])


def plaque(F, name, q):
    M = mats()
    bm = bmesh.new()
    K.box_bm(bm, q[0], q[1], -0.035, 0.0, q[2], q[3])
    hi = K.bm_object(name + "_hi", bm, F.high, F.frame, M["marble"])
    K.weather(hi, wear=0.4, bevel=0.008, subdiv=2)
    bm = bmesh.new()
    K.box_bm(bm, q[0], q[1], -0.035, 0.0, q[2], q[3])
    K.bm_object(name, bm, F.low, F.frame, M["low"])


def sign(F, name, d):
    """Shop sign of the 1980s: painted board over the door with raised letters; optionally a sign on a
    bracket perpendicular to the wall (pharmacy cross, tobacconist's T)."""
    bg = principled(name + "_fondo", d.get("bg", (0.02, 0.05, 0.12)), 0.5)
    fg_col = d.get("fg", (0.75, 0.70, 0.55))
    glow = d.get("glow", 0.0)
    fg = principled(name + "_lettere", fg_col, 0.4)
    if glow:
        b = fg.node_tree.nodes["Principled BSDF"]
        b.inputs["Emission Color"].default_value = (*fg_col, 1)
        b.inputs["Emission Strength"].default_value = glow
    u0, u1, v = d["u0"], d["u1"], d["v"]
    h = d.get("h", 0.45)
    bm = bmesh.new()
    K.box_bm(bm, u0, u1, -0.06, -0.01, v, v + h)
    K.bm_object(name, bm, F.detail, F.frame, bg)
    cu = bpy.data.curves.new(name + "_testo", "FONT")
    cu.body = d["text"]
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.size = h * 0.62
    cu.extrude = 0.008
    cu.space_character = 1.15
    t = bpy.data.objects.new(name + "_testo", cu)
    F.detail.objects.link(t)
    t.parent = F.frame
    t.rotation_euler = (math.pi / 2, 0, 0)
    t.location = ((u0 + u1) / 2, -0.07, v + h / 2)
    cu.materials.append(fg)
    # Fit the text in the board.
    bpy.context.view_layer.update()
    w = t.dimensions.x
    if w > (u1 - u0) * 0.92:
        cu.size *= (u1 - u0) * 0.92 / w
    flag = d.get("flag")
    if flag:
        uf, vf = flag["u"], flag["v"]
        bm = bmesh.new()
        K.box_bm(bm, uf - 0.02, uf + 0.02, -0.75, 0.0, vf + 0.25, vf + 0.29)          # bracket
        K.bm_object(name + "_braccio", bm, F.detail, F.frame, A_iron())
        col = principled(name + "_bandiera", flag["color"], 0.4)
        if flag.get("glow"):
            b = col.node_tree.nodes["Principled BSDF"]
            b.inputs["Emission Color"].default_value = (*flag["color"], 1)
            b.inputs["Emission Strength"].default_value = flag["glow"]
        bm = bmesh.new()
        if flag["shape"] == "cross":
            for a in ((-0.25, 0.25, -0.08, 0.08), (-0.08, 0.08, -0.25, 0.25)):
                K.box_bm(bm, uf - 0.03, uf + 0.03, -0.55 + a[0], -0.55 + a[1], vf + a[2], vf + a[3])
        else:
            K.box_bm(bm, uf - 0.03, uf + 0.03, -0.80, -0.30, vf - 0.25, vf + 0.25)
        K.bm_object(name + "_bandiera", bm, F.detail, F.frame, col)
        if flag["shape"] == "T":
            wt = principled(name + "_T", (0.8, 0.8, 0.8), 0.4)
            bm = bmesh.new()
            for side in (-1, 1):
                x = uf + side * 0.035
                K.box_bm(bm, x - 0.004, x + 0.004, -0.72, -0.38, vf + 0.10, vf + 0.17)
                K.box_bm(bm, x - 0.004, x + 0.004, -0.585, -0.515, vf - 0.17, vf + 0.17)
            K.bm_object(name + "_T", bm, F.detail, F.frame, wt)


def A_iron():
    return mats()["iron"]


def anchor_y(F, name, u, v):
    M = mats()
    bm = bmesh.new()
    K.box_bm(bm, u - 0.02, u + 0.02, -0.03, 0.0, v - 0.28, v)
    for sgn in (-1, 1):
        a = [bm.verts.new((u + sgn * 0.01, -0.03, v)), bm.verts.new((u + sgn * 0.17, -0.03, v + 0.24)),
             bm.verts.new((u + sgn * 0.20, -0.03, v + 0.22)), bm.verts.new((u + sgn * 0.035, -0.03, v - 0.02))]
        b = [bm.verts.new((p.co.x, 0.0, p.co.z)) for p in a]
        bm.faces.new(a if sgn < 0 else list(reversed(a)))
        bm.faces.new(list(reversed(b)) if sgn < 0 else b)
        for i in range(4):
            try:
                bm.faces.new((a[i], a[(i + 1) % 4], b[(i + 1) % 4], b[i]))
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return K.bm_object(name, bm, F.detail, F.frame, M["iron"])


def coppi_eave(F, name, u0, u1, v, out):
    M = mats()
    bm = bmesh.new()
    seg = 8
    u = u0
    k = 0
    rnd = random.Random(hash(name) & 0xFFFF)
    while u < u1:
        r = 0.075
        cu = u + r
        up = k % 2 == 0
        dz = rnd.uniform(-0.012, 0.012)
        dy = rnd.uniform(-0.03, 0.03)
        ring_a, ring_b = [], []
        for j in range(seg + 1):
            a = math.pi * j / seg
            x = cu + r * math.cos(a)
            z = v + dz + (r * math.sin(a) if up else -r * math.sin(a) + 0.02)
            ring_a.append(bm.verts.new((x, -out + dy, z)))
            ring_b.append(bm.verts.new((x, -out + dy + 0.55, z + 0.18)))
        for j in range(seg):
            bm.faces.new((ring_a[j], ring_a[j + 1], ring_b[j + 1], ring_b[j]) if up else (ring_a[j + 1], ring_a[j], ring_b[j], ring_b[j + 1]))
        u += 0.17
        k += 1
    sol = K.bm_object(name, bm, F.detail, F.frame, M["coppi"])
    s = sol.modifiers.new("Solid", "SOLIDIFY")
    s.thickness = 0.015
    return sol


def ivy(F, name, region, density=900, seed=1):
    """Ivy: a mass of small leaves hugging the wall, thicker at the bottom of the region."""
    if os.environ.get("M80_VERDE", "0") != "1":
        # Planted in Unreal: only a marker with the region it covers.
        u0, u1, v0, v1 = region
        mk = bpy.data.objects.new(name, None)
        mk.empty_display_type = "CONE"
        mk.location = ((u0 + u1) / 2, -0.1, v0)
        mk["tipo"], mk["regione_uv"] = "edera", list(region)
        K.collection("Vegetazione_Marker").objects.link(mk)
        mk.parent = F.frame
        return mk
    M = mats()
    rnd = random.Random(seed)
    u0, u1, v0, v1 = region
    bm = bmesh.new()
    n = int((u1 - u0) * (v1 - v0) * density)
    for _ in range(n):
        u = rnd.uniform(u0, u1)
        t = rnd.random() ** 0.7
        v = v0 + (v1 - v0) * (1 - t)
        y = -0.02 - rnd.uniform(0, 0.35) * (0.4 + 0.6 * t)
        s = rnd.uniform(0.04, 0.08)
        a = rnd.uniform(0, math.tau)
        c, d = math.cos(a) * s, math.sin(a) * s
        tilt = rnd.uniform(-0.03, 0.03)
        vs = [bm.verts.new((u + c, y + tilt, v + d)), bm.verts.new((u - d, y - tilt, v + c)),
              bm.verts.new((u - c, y + tilt, v - d)), bm.verts.new((u + d, y - tilt, v - c))]
        bm.faces.new(vs)
    return K.bm_object(name, bm, F.detail, F.frame, M["ivy"])


# ---------------------------------------------------------------------------------------------
# Facade builder

def build(spec, px_per_m=110, step=0.022):
    M = mats()
    F = K.Facade(spec["name"], spec["p0"], spec["p1"], spec["z0"], spec["height"])
    W, H = F.width, spec["height"]
    F.spec = spec
    ops = []
    for o in spec.get("openings", []):
        ops.append((o["id"], K.Opening(o["u0"], o["u1"], o["v0"], o["v1"], o.get("arch", 0.0), o.get("kind", "window"), o.get("depth", 0.32)), o))
    openings = [op for _, op, _ in ops]
    ruin = spec.get("ruin")

    prof = spec.get("top")

    def top_of(U):
        top = np.full(np.shape(U), H)
        if prof:
            top = np.interp(U, [p[0] for p in prof], [p[1] for p in prof])
        if ruin:
            inside = (U > ruin["u0"]) & (U < ruin["u1"])
            jag = ruin["top"] + 1.2 * K.value_noise(U, np.zeros_like(U) + 2.3, 0.6, 5, 3) - 0.6
            top = np.where(inside, np.minimum(top, jag), top)
        return top

    # High wall: displaced grid; albedo image in the wall's own UVs, with run-off streaks.
    def height_fn(U, V):
        return surface(spec, U, V)[0]

    def keep_fn(U, V):
        keep = V < top_of(U)
        for o in openings:
            keep &= ~o.contains(U, V)
        return keep

    nu, nv = int(W * px_per_m), int(H * px_per_m)
    us, vs = np.meshgrid(np.linspace(0, W, nu), np.linspace(0, H, nv))
    h, alb = surface(spec, us, vs)
    regions = []
    for _, o, d in ops:
        if o.kind in ("window", "french"):
            regions.append((o.u0 - 0.2, o.u1 + 0.2, o.v0 - 0.05, 1.6, 0.42))
    for b in spec.get("balconies", []):
        regions.append((b["u0"], b["u1"], b["v"] - 0.5, 2.2, 0.38))
    for b in spec.get("bands", []):
        regions.append((b.get("u0", 0.0), b.get("u1", W), b["v"], 0.9, 0.22))
    if spec.get("cornice"):
        regions.append((0.0, W, spec["cornice"]["v"], 1.4, 0.30))
    lines = K.value_noise(us, np.full(us.shape, 3.7), 0.035, 21, 3)
    for u0, u1, vt, length, strength in regions:
        m = (us > u0) & (us < u1) & (vs < vt) & (vs > vt - length)
        fall = np.clip(1 - (vt - vs) / length, 0, 1) ** 1.5
        side = np.clip(np.minimum(us - u0, u1 - us) / 0.25, 0, 1)
        dark = strength * fall * side * (0.25 + 0.75 * lines)
        alb[m] *= (1 - dark[m])[:, None]
    # Grime: long run-off streaks from the top, a patchy patina, dirt and damp along the street.
    grime = spec.get("grime", 1.0)
    streak = np.clip((K.value_noise(us, vs * 0.025, 0.05, 31, 3) - 0.5) * 2.2, 0, 1)
    from_top = 0.35 + 0.65 * np.clip(1 - (H - vs) / 5.0, 0, 1)
    alb = alb * (1 - grime * 0.24 * streak * from_top)[..., None]
    # Warm dirt, not grey: the stone stays golden under it.
    patina = grime * 0.14 * np.clip((K.value_noise(us, vs, 2.2, 33, 3) - 0.35) * 1.6, 0, 1)
    alb = alb * (1 - patina)[..., None] + np.array([0.16, 0.12, 0.07]) * patina[..., None]
    base_h = 1.3 + 0.6 * K.value_noise(us, np.zeros_like(us), 0.8, 35, 2)
    damp = np.clip(1 - vs / base_h, 0, 1)[..., None] * (0.25 + 0.15 * grime)
    alb = alb * (1 - damp)
    # The image is stored as sRGB: encoded, the walls reach the lightness of the town's Unreal materials (colour check
    # m80_bartoli_palette.py / Scripts/m80_bartoli_colour_compare.py: unencoded the stone came out 15-20 L darker and
    # more orange than the ashlar and rubble of the procedural houses); with 1/1.8 the baked Corso fronts in the town
    # were still L 44 and ochre (b 22) beside the ashlar's L 52, b 15: 1/2.2 and 3/4 of the saturation give L 54, b 15.
    alb = np.clip(alb, 0, 1)
    lum = (alb[..., :3] * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
    alb[..., :3] = lum + (alb[..., :3] - lum) * WALL_SAT
    img = K.image_from_array(spec["name"] + "_albedo", (np.clip(alb, 0, 1) ** WALL_GAMMA).astype(np.float32))
    wall_mat = bpy.data.materials.new(spec["name"] + "_muro_hi")
    wall_mat.use_nodes = True
    t = wall_mat.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = img
    wall_mat.node_tree.links.new(t.outputs[0], wall_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    wall_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.92
    K.grid_mesh(spec["name"] + "_muro_hi", W, H, step, height_fn, keep_fn, F.high, F.frame, wall_mat)
    outline = None
    if ruin or prof:
        us_ = np.linspace(0, W, int(W / 0.25) + 1)
        tops = top_of(us_)
        outline = [(0.0, 0.0), (W, 0.0)] + [(float(u), float(t)) for u, t in zip(us_[::-1], tops[::-1])]
    flat_wall(spec["name"] + "_muro", W, H, openings, F, outline)

    for nm, o, d in ops:
        if o.kind in ("empty",):
            continue
        K.reveal(nm + "_mazzetta_hi", o, F.high, F.frame, M["stone"])
        K.reveal(nm + "_mazzetta", o, F.low, F.frame, M["low"])
        fr = d.get("frame", {"w": 0.16, "proj": 0.055, "mat": "stone"})
        if fr:
            path = list(reversed(o.outline(20)))
            closed = o.kind in ("window", "french")
            mat = M[fr.get("mat", "stone")]
            K.sweep(nm + "_cornice_hi", path, K.frame_profile(fr["w"], fr["proj"], 8), F.high, F.frame, mat, closed=closed, smooth=True)
            K.sweep(nm + "_cornice", path, K.frame_profile(fr["w"], fr["proj"], 1), F.low, F.frame, M["low"], closed=closed)
        if d.get("sill"):
            sill = [(o.u0 - 0.22, o.v0), (o.u1 + 0.22, o.v0)]
            K.sweep(nm + "_davanzale_hi", sill, K.sill_profile(0.12, 6), F.high, F.frame, M["stone"], smooth=True)
            K.sweep(nm + "_davanzale", sill, K.sill_profile(0.12, 1), F.low, F.frame, M["low"])
        if d.get("keystone"):
            for coll, mat, sfx in ((F.high, M[(fr or {}).get("mat", "stone")], "_hi"), (F.low, M["low"], "")):
                bm = bmesh.new()
                mid = (o.u0 + o.u1) / 2
                K.box_bm(bm, mid - 0.16, mid + 0.16, -0.15, 0.0, o.top - 0.05, o.top + 0.45)
                ob = K.bm_object(nm + "_chiave" + sfx, bm, coll, F.frame, mat)
                if sfx:
                    K.add_bevel(ob, 0.03, 3)
                    s = ob.modifiers.new("Sub", "SUBSURF")
                    s.levels = s.render_levels = 3
                    tex = bpy.data.textures.get("M80_Mascherone") or bpy.data.textures.new("M80_Mascherone", "STUCCI")
                    tex.noise_scale = 0.07
                    dsp = ob.modifiers.new("Scolpito", "DISPLACE")
                    dsp.texture = tex
                    dsp.strength = 0.05
                    dsp.texture_coords = "GLOBAL"
        fit = d.get("fit", "none")
        if fit == "shutters":
            shutters(F, nm + "_persiane", o, True)
        elif fit == "shutters_open":
            shutters(F, nm + "_persiane", o, False)
        elif fit == "glazed":
            glazed(F, nm, o)
        elif fit == "grille":
            glazed(F, nm, o, bars=True)
        elif fit == "door":
            door(F, nm + "_porta", o, M[d.get("door_mat", "wood")], inset=0.25, to_v1=d.get("lunette", False))
        elif fit == "portal":
            door(F, nm + "_portone", o, M[d.get("door_mat", "wood")], inset=0.30, knockers=True, to_v1=d.get("lunette", False))
        elif fit == "shop":
            shop_front(F, nm + "_bottega", o)
        elif fit == "roll":
            roll_shutter(F, nm + "_serranda", o)
        elif fit == "rail":
            railing(F, nm + "_ringhiera", o.u0 + 0.02, o.u1 - 0.02, -0.0, o.v0, 1.0, "straight", sides=False)
        if d.get("lunette"):
            lunette(F, nm + "_raggiera", o)
        if d.get("dark", True) and o.kind != "open_arch":
            # Dark interior behind the opening.
            bm = bmesh.new()
            K.box_bm(bm, o.u0 - 0.1, o.u1 + 0.1, o.depth + 0.5, o.depth + 0.52, o.v0, o.top + 0.1)
            K.bm_object(nm + "_buio", bm, F.detail, F.frame, M["dark"])

    for k, (a, b, proj, q) in enumerate(spec.get("pilasters", [])):
        K.ashlar_strip("%s_lesena%d" % (spec["name"], k), a, b, 0.0, min(H, (spec.get("cornice") or {}).get("v", H)), proj, 0.40,
                       F.high, F.low, M["stone"], M["low"], F.frame, seed=k + 1, quoin=0.38 if q else 0.0)
    for k, b in enumerate(spec.get("bands", [])):
        prof = {"string": K.profile_resample([(0.0, 0.0), (0.0, 0.06), (0.10, 0.08), ("arc", 0.13, 0.08, 0.03, 180, 90), (0.18, 0.11), (0.20, 0.11), (0.20, 0.0)], 4),
                "plinth": [(0.0, 0.0), (0.0, 0.07), (b.get("h", 0.6), 0.07), (b.get("h", 0.6) + 0.06, 0.0)],
                "cornice": K.cornice_profile(4)}[b.get("profile", "string")]
        path = [(b.get("u0", 0.0) - 0.04, b["v"]), (b.get("u1", W) + 0.04, b["v"])]
        mat = M[b.get("mat", "stone")]
        K.sweep("%s_fascia%d_hi" % (spec["name"], k), path, prof, F.high, F.frame, mat, smooth=True)
        K.sweep("%s_fascia%d" % (spec["name"], k), path, prof[::2] + [prof[-1]], F.low, F.frame, M["low"])
    c = spec.get("cornice")
    if c:
        prof = K.cornice_profile(10) if c.get("profile", "cornice") == "cornice" else K.frame_profile(0.25, 0.18, 8)
        path = [(-0.06, c["v"]), (W + 0.06, c["v"])]
        K.sweep(spec["name"] + "_cornicione_hi", path, prof, F.high, F.frame, M[c.get("mat", "stone")], smooth=True)
        K.sweep(spec["name"] + "_cornicione", path, K.cornice_profile(2) if c.get("profile", "cornice") == "cornice" else K.frame_profile(0.25, 0.18, 1),
                F.low, F.frame, M["low"])
        if c.get("modillions"):
            modillions(F, spec["name"], 0.0, W, c["v"], M[c.get("mat", "stone")], c["modillions"])
        if c.get("tiles", True):
            coppi_eave(F, spec["name"] + "_coppi", -0.05, W + 0.05, c["v"] + 0.54, 0.50)
    for k, b in enumerate(spec.get("balconies", [])):
        balcony(F, "%s_balcone%d" % (spec["name"], k), b)
    for k, (u, v) in enumerate(spec.get("anchors", [])):
        anchor_y(F, "%s_capochiave%d" % (spec["name"], k), u, v)
    for k, q in enumerate(spec.get("plaques", [])):
        plaque(F, "%s_lapide%d" % (spec["name"], k), q)
    # Shop signs and their symbols (pharmacy cross, tobacconist's T) are off: too plain for the 1980s (M80_INSEGNE=1
    # brings them back).
    for k, d in enumerate(spec.get("signs", []) if os.environ.get("M80_INSEGNE", "0") == "1" else []):
        sign(F, "%s_insegna%d" % (spec["name"], k), d)
    for k, r in enumerate(spec.get("ivy", [])):
        ivy(F, "%s_edera%d" % (spec["name"], k), r, seed=k + 3)
    extra = spec.get("extra")
    if extra:
        extra(F, ops)
    weather_high(F)
    return F


def flat_wall(name, W, H, openings, F, outline=None):
    M = mats()
    bm = bmesh.new()

    def loop(pts):
        vs = [bm.verts.new((u, 0.0, v)) for u, v in pts]
        for i in range(len(vs)):
            bm.edges.new((vs[i], vs[(i + 1) % len(vs)]))

    loop(outline or [(0, 0), (W, 0), (W, H), (0, H)])
    for o in openings:
        loop(o.outline())
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=bm.edges[:], normal=(0, -1, 0))
    for f in bm.faces:
        if f.normal.y > 0:
            f.normal_flip()
    return K.bm_object(name, bm, F.low, F.frame, M["low"])


SWEEPS = ("cornice", "davanzale", "arco", "trabeazione", "timpano", "toro", "cornicione", "fascia")


def weather_high(F):
    """Centuries of weather: no perfectly squared stone anywhere in the high-poly."""
    for ob in list(F.high.objects):
        if ob.type != "MESH" or ob.name.endswith("muro_hi"):
            continue
        if any(m.type == "DISPLACE" for m in ob.modifiers):
            continue
        for m in list(ob.modifiers):
            if m.type == "BEVEL":
                ob.modifiers.remove(m)
        sweep = any(k in ob.name for k in SWEEPS)
        if "mazzetta" in ob.name:
            K.densify(ob, 0.06)
            K.weather(ob, wear=0.6, bevel=0.0, subdiv=1)
        elif sweep:
            K.weather(ob, wear=0.9, bevel=0.0, subdiv=1)
        else:
            K.densify(ob, 0.06)
            K.weather(ob, wear=1.1, bevel=0.015, subdiv=2)
