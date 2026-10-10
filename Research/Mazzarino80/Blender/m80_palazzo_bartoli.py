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


def inside(x, y, poly):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


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


def terrain_mesh(mat, holes=()):
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
            q = (vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i])
            cx = sum(v.co.x for v in q) / 4
            cy = sum(v.co.y for v in q) / 4
            if any(inside(cx, cy, h) for h in holes):
                continue
            bm.faces.new(q)
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


def massing(skip=(), render_it=True):
    if render_it:
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
    prism("B_giardino_pensile", b["poly"], b["floor_top"], b["floor_top"] + 0.05, material("Terra", (0.36, 0.28, 0.20)))

    for key in ("C_palazzo", "D_angolo", "E_ala_nord", "N_via_butera"):
        if key in skip:
            continue
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
    prism("Giardino_alberi", g["poly"], poly_ground(g["poly"]) - 0.5, g["level"], material("Terra", (0.36, 0.28, 0.20)))
    g2 = LAYOUT["giardino_nordest"]
    prism("Giardino_nordest", g2["poly"], poly_ground(g2["poly"]) - 0.5, poly_ground(g2["poly"], max) - 1.0,
          material("Terra", (0.36, 0.28, 0.20)))
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
                              ((25, 25), g2["poly"], None), ((25, 14), g2["poly"], None), ((29, 16), g2["poly"], None)):
        z = lvl if lvl is not None else ground(x, y)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=3.0, location=(x, y, z + 4.5))
        bpy.context.object.data.materials.append(leaf)
        bpy.context.object.color = (*leaf.diffuse_color[:3], 1)

    if not render_it:
        return
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


# ---------------------------------------------------------------------------------------------
# Facade C: high-poly, retopology, UV, bake

TEXTURES = os.path.join(HERE, "Textures", "Bartoli")


def use_gpu():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
            except TypeError:
                continue
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == kind
                bpy.context.scene.cycles.device = "GPU"
                return kind
    except Exception as e:  # noqa: BLE001
        print("GPU not available:", e)
    return "CPU"


def select_only(objs, active):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


def join_low(F):
    objs = [o for o in F.low.objects if o.type == "MESH"]
    select_only(objs, objs[0])
    bpy.ops.object.join()
    low = bpy.context.view_layer.objects.active
    low.name = F.name + "_Low"
    low.data.name = F.name + "_Low"
    # Retopology clean-up: weld coincident vertices, no loose parts, triangulated n-gons stay as quads/tris.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    # UV: islands by angle, packed with a margin; texel density is uniform because the scale is kept.
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    return low


def merged_high(high, name):
    """The high-poly pieces as one temporary mesh (modifiers applied, materials and UV layers kept). The selected-to-
    active bake renders, and re-syncs the whole scene, once per selected object: a facade of ~250 pieces cost ~250
    syncs of 3.5 s per pass with the GPU idle. Object-space noise of the stone now runs in lot space, without seams
    between pieces. M80_BAKE_MERGE=0 bakes the pieces as they are."""
    dg = bpy.context.evaluated_depsgraph_get()
    parts = []
    for o in high:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        if not me.polygons:
            bpy.data.meshes.remove(me)
            continue
        me.transform(o.matrix_world)
        if o.matrix_world.determinant() < 0:
            me.flip_normals()
        ob = bpy.data.objects.new(o.name + "_bake", me)
        bpy.context.scene.collection.objects.link(ob)
        parts.append(ob)
    select_only(parts, parts[0])
    if len(parts) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = name
    return ob


def bake_low(F, low, size):
    import numpy as np
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = int(os.environ.get("M80_SAMPLES", "48"))
    sc.render.bake.margin = 12
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.use_cage = False
    sc.render.bake.cage_extrusion = 0.05
    sc.render.bake.max_ray_distance = 0.14
    mat = low.data.materials[0]
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    images = {}
    high = [o for o in F.high.objects if o.type == "MESH" and not o.hide_render]
    for o in list(F.detail.objects):
        o.hide_render = True   # fittings must not shadow the baked AO
    merged = None
    if os.environ.get("M80_BAKE_MERGE", "1") != "0" and len(high) > 1:
        merged = merged_high(high, F.name + "_HighBake")
        for o in high:
            o.hide_render = True   # no twin surfaces in the occlusion
        high, pieces = [merged], high

    def target(key, colour):
        img = bpy.data.images.new("%s_%s" % (F.name, key), size, size, alpha=False)
        img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        n = nodes.get("BakeTarget") or nodes.new("ShaderNodeTexImage")
        n.name = "BakeTarget"
        n.image = img
        nodes.active = n
        images[key] = img

    select_only(high + [low], low)
    # Colour, normal and roughness only need a few samples (anti-aliasing); the occlusion needs more.
    ao_samples = sc.cycles.samples
    sc.cycles.samples = 4
    target("D", True)
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)
    target("N", False)
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", use_clear=True)
    sc.cycles.samples = 1
    target("R", False)
    bpy.ops.object.bake(type="ROUGHNESS", use_clear=True)
    sc.cycles.samples = ao_samples
    target("AO", False)
    bpy.ops.object.bake(type="AO", use_clear=True)
    for o in list(F.detail.objects):
        o.hide_render = False
    if merged:
        for o in pieces:
            o.hide_render = False
        me = merged.data
        bpy.data.objects.remove(merged)
        bpy.data.meshes.remove(me)
    px = {}
    for k in ("AO", "R"):
        arr = np.empty(size * size * 4, dtype=np.float32)
        images[k].pixels.foreach_get(arr)
        px[k] = arr
    orm = bpy.data.images.new(F.name + "_ORM", size, size, alpha=False)
    orm.colorspace_settings.name = "Non-Color"
    packed = np.ones(size * size * 4, dtype=np.float32)
    packed[0::4], packed[1::4], packed[2::4] = px["AO"][0::4], px["R"][0::4], 0.0
    orm.pixels.foreach_set(packed)
    os.makedirs(TEXTURES, exist_ok=True)
    settings = sc.render.image_settings
    settings.quality = 92
    files = {}
    for key, img, fmt, ext in (("D", images["D"], "JPEG", "jpg"), ("N", images["N"], "PNG", "png"), ("ORM", orm, "JPEG", "jpg")):
        settings.file_format = fmt
        settings.color_mode = "RGB"
        path = os.path.join(TEXTURES, "T_Bartoli_%s_%s.%s" % (F.name, key, ext))
        img.save_render(path, scene=sc)
        files[key] = path
    # The bake targets are on disk now: free them (a whole block of 4K and 2K targets grew Blender to 16 GB).
    nodes["BakeTarget"].image = None
    for img in list(images.values()) + [orm]:
        bpy.data.images.remove(img)
    # The low-poly's own material: baked colour, normal map, AO x colour, roughness.
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    td = nt.nodes.new("ShaderNodeTexImage")
    td.image = bpy.data.images.load(files["D"])
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = bpy.data.images.load(files["N"])
    tn.image.colorspace_settings.name = "Non-Color"
    to = nt.nodes.new("ShaderNodeTexImage")
    to.image = bpy.data.images.load(files["ORM"])
    to.image.colorspace_settings.name = "Non-Color"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(to.outputs[0], sep.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 0.8
    nt.links.new(td.outputs[0], mul.inputs[6])
    nt.links.new(sep.outputs[0], mul.inputs[7])
    nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tn.outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    return files


def sky_and_sun(azimuth_deg=150, elevation_deg=38):
    sc = bpy.context.scene
    world = bpy.data.worlds.new("Cielo")
    world.use_nodes = True
    nt = world.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(elevation_deg)
    sky.sun_rotation = math.radians(azimuth_deg)
    sky.sun_intensity = 0.6
    nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0])
    nt.nodes["Background"].inputs["Strength"].default_value = 0.35
    sc.world = world
    sun = bpy.data.objects.new("Sole", bpy.data.lights.new("Sole", "SUN"))
    sun.data.energy = 3.6
    sun.data.angle = math.radians(0.6)
    sun.rotation_euler = (math.radians(90 - elevation_deg), 0, math.radians(azimuth_deg + 90))
    sc.collection.objects.link(sun)
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.8


def render_views(F, views, tag, show_high):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.image_settings.file_format = "PNG"
    for o in list(F.high.objects):
        o.hide_render = not show_high
    for o in list(F.low.objects):
        o.hide_render = show_high
    cam = bpy.data.objects.get("CamFacciata") or bpy.data.objects.new("CamFacciata", bpy.data.cameras.new("CamFacciata"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    M = F.frame.matrix_world
    for name, (eye, target, fov) in views.items():
        e, t = M @ Vector(eye), M @ Vector(target)
        cam.location = e
        cam.rotation_euler = (t - e).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens_unit = "FOV"
        cam.data.angle = math.radians(fov)
        sc.render.filepath = os.path.join(PREVIEWS, "facciataC_%s_%s.png" % (name, tag))
        bpy.ops.render.render(write_still=True)


def facade_c():
    import m80_bartoli_facades as BF
    reset()
    print("GPU:", use_gpu())
    terrain_mesh(material("Terreno", (0.42, 0.40, 0.33)))
    neighbours(material("Vicini", (0.62, 0.62, 0.62)))
    F = BF.build_facade_c()
    # Body behind the facade, so the openings show a dark interior and the roof closes the top.
    roof = material("Coppi_massa", (0.50, 0.30, 0.22))
    w = LAYOUT["bodies"]["C_palazzo"]["wings"][0]
    poly = [list(p) for p in w["poly"]]
    back = [(-0.35 * 0.283 + x, 0.35 * 0.959 + y) for x, y in poly[:2]]   # 35 cm behind the facade plane
    inner = back + [tuple(p) for p in poly[2:]]
    prism("C_massa", inner, 0.5, 0.9 + 12.0, material("Interno", (0.08, 0.07, 0.06)))
    hip_roof("C_tetto", poly, 0.9 + 12.0 + 0.15, w["axis"], 22, roof, overhang=0.0)
    sky_and_sun()
    t0 = time.time()
    low = join_low(F)
    size = int(os.environ.get("M80_BAKE_SIZE", "4096"))
    files = bake_low(F, low, size)
    print("bake %.0f s" % (time.time() - t0), files)
    views = {
        "fronte": ((11.0, -21.0, 1.7), (11.0, 0.0, 6.2), 62),
        "portale": ((15.3, -6.5, 1.8), (15.3, 0.0, 4.3), 62),
        "radente": ((-4.0, -9.0, 1.7), (12.0, 0.0, 6.0), 55),
    }
    render_views(F, views, "alta", True)
    render_views(F, views, "bassa", False)
    stats = {}
    for tag, col in (("alta", F.high), ("bassa", F.low), ("dettagli", F.detail)):
        dg = bpy.context.evaluated_depsgraph_get()
        tris = 0
        for o in list(col.objects):
            if o.type in ("MESH", "CURVE"):
                me = o.evaluated_get(dg).to_mesh()
                tris += sum(len(p.vertices) - 2 for p in me.polygons)
                o.evaluated_get(dg).to_mesh_clear()
        stats[tag] = tris
    print("triangles", stats)
    with open(os.path.join(PREVIEWS, "facciataC_stats.json"), "w") as f:
        json.dump({"triangles": stats, "textures": {k: os.path.basename(v) for k, v in files.items()}, "size": size}, f, indent=1)
    os.makedirs(SAVED, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAVED, "bartoli_facciataC.blend"))


def preview_c():
    """High-poly only (no bake, no retopology): views from where the reference photos were taken."""
    import m80_bartoli_facades as BF
    reset()
    print("GPU:", use_gpu())
    massing(skip=("C_palazzo",), render_it=False)
    F = BF.build_facade_c()
    w = LAYOUT["bodies"]["C_palazzo"]["wings"]
    poly = [list(p) for p in w[0]["poly"]]
    back = [(-0.35 * 0.283 + x, 0.35 * 0.959 + y) for x, y in poly[:2]]
    prism("C_massa", back + [tuple(p) for p in poly[2:]], 0.5, 0.9 + 12.0, material("Interno", (0.08, 0.07, 0.06)))
    hip_roof("C_tetto", poly, 0.9 + 12.0 + 0.15, w[0]["axis"], 22, material("Coppi_massa", (0.50, 0.30, 0.22)), overhang=0.0)
    prism("C_ala_ovest", w[1]["poly"], 0.5, 0.9 + 12.0, material("C_palazzo", (0.62, 0.50, 0.34)))
    hip_roof("C_tetto_ovest", w[1]["poly"], 0.9 + 12.0, w[1]["axis"], 22, material("Coppi_massa", (0.50, 0.30, 0.22)))
    sky_and_sun()
    views = {
        "foto_frontale": ((11.0, -21.0, 1.7), (11.0, 0.0, 6.2), 62),
        "foto_222_corso": ((17.5, -7.5, 1.6), (9.0, 0.0, 7.5), 92),
        "foto_220_corso": ((5.0, -6.0, 1.6), (5.0, 0.0, 8.5), 100),
        "foto_271_corso": ((25.0, -9.0, 1.6), (14.0, 0.0, 6.5), 92),
        "portale_balcone": ((15.3, -5.0, 2.0), (15.3, 0.0, 4.8), 72),
        "radente_ovest": ((-5.0, -7.0, 1.7), (12.0, 0.0, 6.0), 60),
    }
    sc = bpy.context.scene
    sc.cycles.samples = 64
    render_views(F, views, "anteprima", True)
    os.makedirs(SAVED, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAVED, "bartoli_anteprimaC.blend"))


# ---------------------------------------------------------------------------------------------
# The whole block in high-poly (before retopology and bake)

CINEMA_ID = "372573548"
# OSM outline, except the south end: the front closes the top of Salita Teatro against the cream house's corner
# (m80_bartoli_facades.CINEMA_FRONT), not 9 m further south on the street.
CINEMA = [(-49.46, -0.07), (-49.08, -1.05), (-48.46, -1.6), (-47.67, -1.64), (-42.0, -0.4),
          (-36.6, 1.5), (-34.8, 7.0), (-38.4, 19.9), (-40.9, 18.8), (-43.0, 25.3), (-52.7, 22.1), (-50.8, 15.7), (-52.9, 15.0),
          (-52.4, 11.9)]
CREMA = [(-40.1, -9.1), (-29.6, -5.5), (-30.6, -2.6), (-27.6, -1.9), (-31.0, 8.0), (-34.8, 7.0), (-36.6, 1.5), (-42.0, -0.4)]
# D is two buildings on the Corso: the lower house of the carriage gate (west) and the corner palace (east), split at
# the lot vertex where their fronts meet (m80_bartoli_facades.D_CORSO_P0).
D_OVEST = [(3.55, -11.5), (8.2, -26.2), (24.9, -19.8), (25.2, -3.5), (9.8, -4.9), (11.5, -7.9)]
D_ANGOLO = [(24.9, -19.8), (42.73, -11.99), (38.4, -0.06), (33.5, -1.8), (25.2, -3.5)]
RUIN = [(38.4, -0.06), (37.0, 3.8), (34.0, 2.8), (34.7, 0.2), (33.5, -1.8)]


def inset(poly, d):
    poly = ccw(poly)
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)), Vector((-e1.y, e1.x))
        b = n0 + n1
        b = b.normalized() / max(0.3, b.normalized().dot(n0)) if b.length > 1e-6 else n0
        q = p1 + b * d
        out.append((q.x, q.y))
    return out


def ring_wall(name, poly, z0, z1, d0, d1, mat):
    """A wall ring between two insets of a footprint (inner faces of a garden parapet, etc.)."""
    a, b = inset(poly, d0), inset(poly, d1)
    bm = bmesh.new()
    n = len(a)
    A0 = [bm.verts.new((x, y, z0)) for x, y in a]
    A1 = [bm.verts.new((x, y, z1)) for x, y in a]
    B0 = [bm.verts.new((x, y, z0)) for x, y in b]
    B1 = [bm.verts.new((x, y, z1)) for x, y in b]
    for i in range(n):
        j = (i + 1) % n
        for f in ((A1[i], A1[j], B1[j], B1[i]), (B0[i], B0[j], B1[j], B1[i])):
            try:
                bm.faces.new(f)
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_object(name, bm, mat)


def bodies_massing(skip=()):
    """Dark interiors 40 cm behind the facades, roofs on the cornices, flat roofs, the ruin."""
    dark = material("Interno", (0.05, 0.045, 0.04))
    roof = material("Coppi_tetto", (0.36, 0.17, 0.10))
    B = LAYOUT["bodies"]
    jobs = [("C0", B["C_palazzo"]["wings"][0]["poly"], 12.95, B["C_palazzo"]["wings"][0]["axis"]),
            ("C1", B["C_palazzo"]["wings"][1]["poly"], 12.95, B["C_palazzo"]["wings"][1]["axis"]),
            ("D_ovest", D_OVEST, 13.95, B["D_angolo"]["wings"][0]["axis"]),
            ("D", D_ANGOLO, 16.95, B["D_angolo"]["wings"][0]["axis"]),
            ("E", B["E_ala_nord"]["wings"][0]["poly"], 13.85, B["E_ala_nord"]["wings"][0]["axis"]),
            ("N", B["N_via_butera"]["wings"][0]["poly"], 17.2, B["N_via_butera"]["wings"][0]["axis"]),
            ("Cinema", CINEMA, 15.2, (0.08, 1.0))]
    import m80_arch_roofs as R
    th, tl = K.collection("Tetti_High"), K.collection("Tetti_Low")
    low = bpy.data.materials.get("Cotto_facciata") or roof
    for name, poly, eave, axis in jobs:
        if name in ("C0", "C1") and "C" in skip:
            # The piano nobile is carved out of the palace's interior volume.
            prism("Massa_%s_basso" % name, inset(poly, 0.4), poly_ground(poly) - 0.5, 0.9 + 4.95, dark)
            prism("Massa_%s_alto" % name, inset(poly, 0.4), 0.9 + 9.05, eave, dark)
        elif name not in skip:
            prism("Massa_" + name, inset(poly, 0.4), poly_ground(poly) - 0.5, eave, dark)
        elif name == "Cinema":
            prism("Massa_Cinema_base", inset(poly, 0.4), poly_ground(poly) - 0.5, 5.3, dark)
        R.hip_roof("Tetto_" + name, poly, eave, axis, 21, th, tl, low)
    # Cream house: flat roof terrace with a parapet; old body B: hanging garden floor and inner walls.
    prism("Massa_Crema", inset(CREMA, 0.4), poly_ground(CREMA) - 0.5, 5.2 + 14.4, dark)
    ring_wall("Crema_parapetto", CREMA, 5.2 + 14.4, 5.2 + 15.4, 0.05, 0.35, material("Intonaco_crema", (0.70, 0.62, 0.48)))
    b = B["B_corpo_antico"]["poly"]
    prism("Massa_B", inset(b, 0.4), poly_ground(b) - 0.5, 6.0, dark)
    ring_wall("B_muri_pensile", b, 6.0, 10.4, 0.05, 0.55, material("Pietrame_interno", (0.40, 0.31, 0.20)))
    # The ruin: rubble on the ground, stumps of the side walls, a fig tree.
    prism("Rudere_macerie", RUIN, poly_ground(RUIN) - 0.3, poly_ground(RUIN) + 0.6, material("Macerie", (0.30, 0.24, 0.16)))


def build_all(step):
    import m80_arch_facade as A
    import m80_bartoli_facades as BF
    import m80_bartoli_site as S
    reset()
    print("GPU:", use_gpu())
    holes = [[to_local(p[0], p[1]) for p in TERRAIN["footprint"]], CINEMA, CREMA, LAYOUT["cortile"]["poly"],
             LAYOUT["giardino_alberi"]["poly"], LAYOUT["giardino_nordest"]["poly"]]
    terrain_mesh(material("Terreno", (0.42, 0.40, 0.33)), holes)
    vic = material("Vicini", (0.62, 0.62, 0.62))
    col = bpy.data.collections.new("Vicini")
    bpy.context.scene.collection.children.link(col)
    for it in PLAN:
        if it["id"] in (LOT, CINEMA_ID):
            continue
        cxl, cyl = to_local(it["center_cm"][0], it["center_cm"][1])
        if abs(cxl) > 75 or abs(cyl) > 70:
            continue
        poly = [to_local(x, y) for x, y in it["ring_cm"]]
        if len(poly) >= 3:
            prism("Vicino_" + it["id"], poly, poly_ground(poly) - 0.3, poly_ground(poly, max) + max(6.5, min(12.0, it.get("height_m", 8.0))), vic, col)
    t0 = time.time()
    built = {}
    for spec in BF.all_specs() + BF.secondary_specs(ground) + S.wall_specs(ground) + [S.facade_n(ground)]:
        built[spec["name"]] = A.build(spec, step=step)
        print("facade %s %.0f s" % (spec["name"], time.time() - t0))
    for k in range(len([n for n in built if n.startswith("Muro_cinta")])):
        F = built["Muro_cinta%d" % k]
        p0, p1 = F.spec["p0"], F.spec["p1"]
        d = Vector((p1[0] - p0[0], p1[1] - p0[1])).normalized()
        n = Vector((-d.y, d.x)) * 0.5
        top = max(t[1] for t in F.spec["top"]) + F.spec["z0"]
        prism("Muro_cinta%d_spessore" % k, [p0, p1, (p1[0] + n.x, p1[1] + n.y), (p0[0] + n.x, p0[1] + n.y)], F.spec["z0"], top - 0.1,
              material("Pietrame_interno", (0.40, 0.31, 0.20)))
    S.staircase_loggia()
    gate = built["D_Corso_ovest"].frame.matrix_world @ Vector((2.5, 0.65, 0.0))
    court = built["Cortile_Sud"].frame.matrix_world @ Vector((7.7, 0.65, 0.0))
    S.androne((gate.x, gate.y), (court.x, court.y))
    S.ground_patch("Cortile", LAYOUT["cortile"]["poly"], LAYOUT["cortile"]["level"], "setts", K.collection("Cortile_High"), K.collection("Cortile_Low"))
    S.gardens(LAYOUT, ground)
    interni = os.environ.get("M80_INTERNI", "1") == "1"
    bodies_massing(skip=("Cinema", "C") if interni else ())
    if interni:
        import m80_bartoli_interni as I
        import m80_bartoli_pianonobile as PN
        I.cinema()
        PN.build(built["C_Corso"].frame)
        # Openings that now look into rooms lose their dark plate.
        for nm in ("C_F1", "C_F2", "C_F3", "C_F4", "C_F5", "CS_P1_2", "CS_P1_3", "CO_P1_0", "CO_P1_1"):
            ob = bpy.data.objects.get(nm + "_buio")
            if ob:
                bpy.data.objects.remove(ob)
    sky_and_sun()
    print("built in %.0f s" % (time.time() - t0))
    return built


def photo_views():
    """Cameras where the reference photos were taken (world coords: eye, target, horizontal fov)."""
    g = lambda x, y, h=1.6: ground(x, y) + h  # noqa: E731
    return {
        "frontale_bartoli": ((-1.1, -46.5, g(-1.1, -46.5)), (-2.0, -29.4, 7.1), 62),
        "corso_222": ((13.0, -38.0, g(13.0, -38.0)), (6.0, -24.0, 8.5), 95),
        "corso_271": ((18.0, -33.0, g(18.0, -33.0)), (6.0, -26.0, 7.0), 95),
        "angolo_farmacia": ((53.0, -25.0, g(53.0, -25.0)), (40.0, -11.5, 9.0), 100),
        "corso_ovest_b": ((-36.0, -41.5, g(-36.0, -41.5)), (-14.0, -33.0, 5.5), 80),
        "salita_teatro": ((-37.5, -31.0, g(-37.5, -31.0)), (-44.0, -9.0, 9.0), 90),
        "cortile_scalone": ((5.5, -9.5, 2.7), (-2.6, 6.5, 6.0), 95),
        "cortile_da_loggia": ((-2.6, 7.6, 7.4), (5.5, -10.0, 4.0), 95),
        "giardino_loggia": ((-13.0, 12.0, 9.2), (-2.5, 6.5, 7.5), 85),
        "via_butera": ((43.5, 37.0, g(43.5, 37.0)), (28.0, 33.5, 9.5), 85),
        "salone": ("PN", (9.8, 6.3, 6.6), (16.0, 1.0, 6.4), 90),
        "pranzo": ("PN", (5.4, 6.3, 6.6), (8.6, 1.2, 6.0), 90),
        "biblioteca": ("PN", (15.6, 9.2, 6.6), (20.5, 13.6, 6.6), 90),
        "anticamera_dal_ballatoio": ("PN", (13.5, 20.05, 6.6), (9.2, 19.0, 6.2), 85),
        "cinema_platea": ((-45.2, 2.2, 8.2), (-45.2, 16.0, 7.6), 85),
        "cinema_galleria": ((-46.0, -4.6, 13.2), (-45.0, 16.0, 7.5), 80),
        "cinema_foyer": ((-45.0, -8.6, 8.0), (-48.5, -3.0, 7.4), 90),
        "aereo_sudest": ((70.0, -75.0, 55.0), (0.0, -5.0, 6.0), 50),
        "aereo_nordovest": ((-60.0, 60.0, 50.0), (-5.0, -5.0, 6.0), 50),
    }


def render_world(views, tag, samples=64):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.image_settings.file_format = "PNG"
    for c in bpy.data.collections:
        if c.name.endswith("_Low"):
            for o in list(c.objects):
                o.hide_render = True
    cam = bpy.data.objects.get("CamMondo") or bpy.data.objects.new("CamMondo", bpy.data.cameras.new("CamMondo"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    for name, view in views.items():
        if view[0] == "PN":
            # Piano nobile views are given in the Corso facade frame (u, w, v).
            fr = bpy.data.objects.get("PianoNobile_Frame")
            if not fr:
                continue
            _, eye, target, fov = view
            eye, target = fr.matrix_world @ Vector(eye), fr.matrix_world @ Vector(target)
        else:
            eye, target, fov = view
        cam.location = eye
        cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens_unit = "FOV"
        cam.data.angle = math.radians(fov)
        sc.render.filepath = os.path.join(PREVIEWS, "%s_%s.png" % (tag, name))
        bpy.ops.render.render(write_still=True)
        print("render", name)


if STAGE == "massing":
    massing()
elif STAGE == "alta":
    import time
    sys.path.append(HERE)
    import m80_arch_kit as K
    build_all(float(os.environ.get("M80_WALL_STEP", "0.03")))
    os.makedirs(SAVED, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAVED, "bartoli_alta.blend"))
    only = [v for v in os.environ.get("M80_VIEWS", "").split(",") if v]
    views = {k: v for k, v in photo_views().items() if not only or k in only}
    render_world(views, "alta", int(os.environ.get("M80_SAMPLES", "64")))
elif STAGE == "anteprima_c":
    sys.path.append(HERE)
    preview_c()
elif STAGE == "facciata_c":
    import time
    sys.path.append(HERE)
    facade_c()
