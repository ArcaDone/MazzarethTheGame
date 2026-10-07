"""Palazzo Bartoli (OSM "Palazzo Branciforti", lot 1249067196) on the Corso of Mazzarino, built in Blender.

Data: Lots/1249067196_layout.json (bodies, courtyard, gardens, levels, in local metres) and
Lots/1249067196_terrain.json (game terrain + footprint, from Scripts/m80_lot_terrain_export.py).
Stage "massing": terrain, neighbours as plain blocks, the bodies with hip roofs, courtyard, staircase and
loggia, gardens; preview renders from the viewpoints of the reference photos.
Run: blender -b --factory-startup --python m80_palazzo_bartoli.py -- massing
Out: Previews/Bartoli/<stage>_*.png, Saved/Mazzarino80/Bartoli/bartoli_<stage>.blend
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LOT = "1249067196"
LAYOUT = json.load(open(os.path.join(HERE, "Lots", LOT + "_layout.json"), encoding="utf-8"))
TERRAIN = json.load(open(os.path.join(HERE, "Lots", LOT + "_terrain.json"), encoding="utf-8"))
PLAN = json.load(open(os.path.join(ROOT, "Research", "Mazzarino80", "building_footprint_plan.json"), encoding="utf-8"))
STAGE = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "massing"
PREVIEWS = os.path.join(HERE, "Previews", "Bartoli")
SAVED = os.path.join(ROOT, "Saved", "Mazzarino80", "Bartoli")
OX, OY, OZ = LAYOUT["origin_world_cm"]


# ---------------------------------------------------------------------------------------------
# Terrain

G = TERRAIN["grid"]


def to_local(wx, wy):
    return (wx - OX) / 100.0, -(wy - OY) / 100.0


def ground(x, y):
    """Game terrain height (local metres) at a local point, bilinear on the exported grid."""
    wx, wy = OX + x * 100.0, OY - y * 100.0
    fi, fj = (wx - G["x0"]) / G["step"], (wy - G["y0"]) / G["step"]
    i, j = max(0, min(G["nx"] - 2, int(fi))), max(0, min(G["ny"] - 2, int(fj)))
    u, v = min(max(fi - i, 0), 1), min(max(fj - j, 0), 1)
    z = G["z"]
    h = (z[j][i] * (1 - u) + z[j][i + 1] * u) * (1 - v) + (z[j + 1][i] * (1 - u) + z[j + 1][i + 1] * u) * v
    return (h - OZ) / 100.0


def poly_ground(poly, fn=min):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    samples = [ground(x, y) for x, y in poly]
    samples.append(ground(sum(xs) / len(xs), sum(ys) / len(ys)))
    return fn(samples)


# ---------------------------------------------------------------------------------------------
# Scene helpers

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, color, rough=0.8):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.roughness = rough
    return m


def mesh_object(name, bm, mat=None, collection=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
        ob.color = (*mat.diffuse_color[:3], 1)
    return ob


def ccw(poly):
    a = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    return poly if a > 0 else list(reversed(poly))


def prism(name, poly, z0, z1, mat, collection=None):
    poly = ccw(poly)
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in poly]
    hi = [bm.verts.new((x, y, z1)) for x, y in poly]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    n = len(poly)
    for i in range(n):
        bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    return mesh_object(name, bm, mat, collection)


def hip_roof(name, poly, eave, axis, pitch_deg, mat, collection=None, overhang=0.35):
    """Hip roof over a footprint: every eave edge rises to the ridge, a segment on the long axis."""
    poly = ccw(poly)
    ax = Vector((axis[0], axis[1])).normalized()
    nx = Vector((-ax.y, ax.x))
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    c = Vector((cx, cy))
    along = [(Vector(p) - c).dot(ax) for p in poly]
    across = [(Vector(p) - c).dot(nx) for p in poly]
    mid = (max(across) + min(across)) / 2
    half = (max(across) - min(across)) / 2
    c = c + nx * mid
    a0, a1 = min(along) + half, max(along) - half
    if a1 < a0:
        a0 = a1 = (min(along) + max(along)) / 2
    rise = math.tan(math.radians(pitch_deg)) * half
    # Eave ring pushed out by the overhang along the vertex bisectors.
    n = len(poly)
    ring = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((e0.y, -e0.x)), Vector((e1.y, -e1.x))
        b = (n0 + n1)
        b = b.normalized() / max(0.3, b.normalized().dot(n0)) if b.length > 1e-6 else n0
        ring.append(p1 + b * overhang)
    bm = bmesh.new()
    eave_v = [bm.verts.new((p.x, p.y, eave)) for p in ring]
    ridge_cache = {}

    def ridge(p):
        t = max(a0, min(a1, (Vector(p) - c).dot(ax)))
        key = round(t, 2)
        if key not in ridge_cache:
            q = c + ax * t
            ridge_cache[key] = bm.verts.new((q.x, q.y, eave + rise))
        return ridge_cache[key]

    for i in range(n):
        a, b = eave_v[i], eave_v[(i + 1) % n]
        ra, rb = ridge(poly[i]), ridge(poly[(i + 1) % n])
        try:
            bm.faces.new((a, b, rb, ra) if ra is not rb else (a, b, ra))
        except ValueError:
            pass
    bm.faces.new(list(reversed(eave_v)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_object(name, bm, mat, collection)


def terrain_mesh(mat):
    nx, ny = G["nx"], G["ny"]
    bm = bmesh.new()
    vs = []
    for j in range(ny):
        row = []
        for i in range(nx):
            x, y = to_local(G["x0"] + i * G["step"], G["y0"] + j * G["step"])
            row.append(bm.verts.new((x, y, (G["z"][j][i] - OZ) / 100.0)))
        vs.append(row)
    for j in range(ny - 1):
        for i in range(nx - 1):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_object("Terreno", bm, mat)


def neighbours(mat):
    col = bpy.data.collections.new("Vicini")
    bpy.context.scene.collection.children.link(col)
    for it in PLAN:
        if it["id"] == LOT:
            continue
        cxl, cyl = to_local(it["center_cm"][0], it["center_cm"][1])
        if abs(cxl) > 62 or abs(cyl) > 62:
            continue
        poly = [to_local(x, y) for x, y in it["ring_cm"]]
        if len(poly) < 3:
            continue
        z0 = poly_ground(poly, min) - 0.3
        z1 = poly_ground(poly, max) + max(6.5, min(12.0, it.get("height_m", 8.0)))
        prism("Vicino_" + it["id"], poly, z0, z1, mat, col)


# ---------------------------------------------------------------------------------------------
# Massing

def offset_line(a, b, d):
    a, b = Vector(a), Vector(b)
    n = (b - a).normalized()
    n = Vector((-n.y, n.x))
    return a + n * d, b + n * d


def massing():
    reset()
    sc = bpy.context.scene
    terrain_mesh(material("Terreno", (0.42, 0.40, 0.33)))
    neighbours(material("Vicini", (0.62, 0.62, 0.62)))
    roof = material("Coppi", (0.55, 0.30, 0.22))
    lv = LAYOUT["levels"]
    B = LAYOUT["bodies"]

    b = B["B_corpo_antico"]
    m = material("B", b["color"])
    base = poly_ground(b["poly"]) - 0.5
    prism("B_piano_terra", b["poly"], base, b["floor_top"], m)
    # Hanging garden: parapet walls 0.8 m thick around the roof garden, and its lawn.
    bm = bmesh.new()
    poly = ccw(b["poly"])
    n = len(poly)
    for i in range(n):
        p, q = Vector(poly[i]), Vector(poly[(i + 1) % n])
        d = (q - p).normalized()
        inward = Vector((-d.y, d.x)) * 0.8
        quad = [p, q, q + inward, p + inward]
        lo = [bm.verts.new((v.x, v.y, b["floor_top"])) for v in quad]
        hi = [bm.verts.new((v.x, v.y, b["parapet_top"])) for v in quad]
        bm.faces.new(lo[::-1])
        bm.faces.new(hi)
        for k in range(4):
            bm.faces.new((lo[k], lo[(k + 1) % 4], hi[(k + 1) % 4], hi[k]))
    mesh_object("B_muri_giardino_pensile", bm, m)
    prism("B_giardino_pensile", b["poly"], b["floor_top"], b["floor_top"] + 0.05, material("Prato", (0.30, 0.45, 0.22)))

    for key in ("C_palazzo", "D_angolo", "E_ala_nord", "N_via_butera"):
        body = B[key]
        m = material(key, body["color"])
        for k, w in enumerate(body["wings"]):
            base = poly_ground(w["poly"]) - 0.5
            prism("%s_%d" % (key, k), w["poly"], base, w["eave"], m)
            hip_roof("%s_tetto_%d" % (key, k), w["poly"], w["eave"], w["axis"], 22, roof)

    c = LAYOUT["cortile"]
    prism("Cortile", c["poly"], poly_ground(c["poly"]) - 0.3, c["level"], material("Basolato", (0.55, 0.52, 0.48)))

    # Staircase (stepped block) and loggia with three arches, along the north edge of the courtyard.
    s = LAYOUT["scalone_loggia"]
    a, bpt = s["front"]
    stone = material("Pietra", (0.85, 0.80, 0.68))
    steps = 14
    for k in range(steps):
        p0, p1 = offset_line(a, bpt, -s["depth_stairs"] * (1 - k / steps))
        q0, q1 = offset_line(a, bpt, 0.0)
        z = c["level"] + (lv["loggia"] - c["level"]) * (k + 1) / steps
        prism("Scalone_%02d" % k, [tuple(p0), tuple(p1), tuple(q1), tuple(q0)], c["level"] - 0.2, z, stone)
    l0, l1 = offset_line(a, bpt, s["depth_loggia"])
    prism("Loggia_piano", [a, bpt, tuple(l1), tuple(l0)], c["level"], lv["loggia"], stone)
    # Arches: four piers and the beam above.
    A, Bv = Vector(a), Vector(bpt)
    d = (Bv - A)
    nrm = Vector((-d.y, d.x)).normalized()
    for k in range(4):
        p = A + d * (k / 3)
        t = d.normalized() * 0.35
        r = nrm * 0.35
        prism("Loggia_pilastro_%d" % k, [tuple(p - t - r), tuple(p + t - r), tuple(p + t + r), tuple(p - t + r)],
              lv["loggia"], lv["loggia"] + 4.2, stone)
    p0, p1 = A - nrm * 0.4, Bv - nrm * 0.4
    prism("Loggia_trave", [tuple(p0), tuple(p1), tuple(p1 + nrm * 0.8), tuple(p0 + nrm * 0.8)],
          lv["loggia"] + 4.2, lv["loggia"] + 5.0, stone)

    g = LAYOUT["giardino_alberi"]
    prism("Giardino_alberi", g["poly"], poly_ground(g["poly"]) - 0.5, g["level"], material("Prato", (0.30, 0.45, 0.22)))
    g2 = LAYOUT["giardino_nordest"]
    prism("Giardino_nordest", g2["poly"], poly_ground(g2["poly"]) - 0.5, poly_ground(g2["poly"], max) - 1.0,
          material("Prato", (0.30, 0.45, 0.22)))
    wall = material("Muro_cinta", (0.70, 0.58, 0.40))
    sw = g2["street_wall"]
    for k in range(len(sw) - 1):
        p, q = Vector(sw[k]), Vector(sw[k + 1])
        dd = (q - p).normalized()
        inn = Vector((-dd.y, dd.x)) * 0.6
        z0 = min(ground(p.x, p.y), ground(q.x, q.y)) - 0.5
        z1 = max(ground(p.x, p.y), ground(q.x, q.y)) + g2["wall_height"]
        prism("Muro_cinta_%d" % k, [tuple(p), tuple(q), tuple(q + inn), tuple(p + inn)], z0, z1, wall)
    # Trees as simple spheres for scale.
    leaf = material("Alberi", (0.18, 0.32, 0.14))
    for (x, y), poly, lvl in (((-12, 12), g["poly"], g["level"]), ((-20, 16), g["poly"], g["level"]), ((-6, 15), g["poly"], g["level"]),
                              ((28, 25), g2["poly"], None), ((25, 14), g2["poly"], None), ((31, 18), g2["poly"], None)):
        z = lvl if lvl is not None else ground(x, y)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=3.0, location=(x, y, z + 4.5))
        bpy.context.object.data.materials.append(leaf)
        bpy.context.object.color = (*leaf.diffuse_color[:3], 1)

    shots = {
        "aereo_sudest": ((75, -85, 62), (4, 0, 6), 35),
        "corso_palazzo": ((3.6, -46.0, 2.6), (-2.2, -29.0, 9.0), 70),
        "corso_ovest": ((-26, -50, 2.6), (-20, -33, 7), 75),
        "piazza_angolo": ((58, -27, 2.6), (40, -12, 10), 70),
        "cortile_da_loggia": ((-2.6, 8.5, 8.6), (3, -12, 5), 80),
        "via_butera": ((24, 46, 10.0), (29, 33, 10), 80),
    }
    render(shots, top=True)


# ---------------------------------------------------------------------------------------------
# Render

def render(shots, top=False):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "OBJECT"
    sh.show_shadows = True
    sh.show_cavity = True
    sh.cavity_type = "WORLD"
    sc.display.light_direction = (0.45, -0.55, 0.70)
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    os.makedirs(PREVIEWS, exist_ok=True)
    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    for name, (eye, target, fov) in shots.items():
        cam_data.type = "PERSP"
        cam_data.lens_unit = "FOV"
        cam_data.angle = math.radians(fov)
        cam.location = eye
        cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(PREVIEWS, "%s_%s.png" % (STAGE, name))
        bpy.ops.render.render(write_still=True)
    if top:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = 112
        cam.location = (2, 2, 120)
        cam.rotation_euler = (0, 0, 0)
        sc.render.resolution_x, sc.render.resolution_y = 1200, 1200
        sc.render.filepath = os.path.join(PREVIEWS, "%s_pianta.png" % STAGE)
        bpy.ops.render.render(write_still=True)
    os.makedirs(SAVED, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAVED, "bartoli_%s.blend" % STAGE))


if STAGE == "massing":
    massing()
