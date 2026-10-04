"""Blender 4.3: clean, optimise and export one asset of D:/Blender/AssetsMazzarethTheGame for Unreal.

Run: blender -b <file.blend> --python m80_prepare_vehicle.py -- <key> <out_dir>
key: Panda | Fiat127 | FiatUno | Golf | Vespa | Poste (see ASSETS)

What it does (the source .blend is never saved):
- keeps only what is visible and rendered; drops lights, cameras, hidden variants, ground planes and
  sky boxes; turns curves/text/instances into meshes; caps subdivision (1 level, 0 on dense meshes)
  and applies all modifiers; removes duplicated objects (same triangles in the same place);
- cars: finds the wheels from the geometry (the round parts touching the ground and what sits inside
  them: rims, hubcaps, brakes, nuts), puts the car at its real length, front along +X, wheels on the
  ground (z = 0), centre between the axles at the origin, and builds the skeleton Root + Wheel_FL/FR/
  RL/RR (FL = front left) like the drivable Fiat 126; body and wheels are reduced to a triangle budget;
- bike: same as a car with two wheels (Root + Wheel_F/Wheel_R); building: one static mesh (parts in
  "split" as meshes of their own);
- images: only the used ones, at most 2048 px, duplicates merged, saved as PNG;
- materials: base colour (or texture), metallic, roughness, glass, emission, normal map -> JSON, so the
  Unreal import script rebuilds them on a few master materials (no baking of the procedural ones).
Writes <out_dir>/<key>.fbx, <out_dir>/Textures/*.png, <out_dir>/<key>.json.
"""
import json
import math
import os
import re
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
KEY, OUT = ARGS[0], ARGS[1]

# Real sizes: length bumper to bumper (m). Budgets in triangles.
ASSETS = {
    "Panda": {"kind": "car", "length": 3.38, "front": 1},
    "Fiat127": {"kind": "car", "length": 3.595},
    "FiatUno": {"kind": "car", "length": 3.645},
    "Golf": {"kind": "car", "length": 3.705},
    "Vespa": {"kind": "bike", "length": 1.77},
    "Poste": {"kind": "building", "scale": 1.0, "split": ["Antenna"]},   # the radio mast is its own mesh
}
CFG = ASSETS[KEY]
BODY_BUDGET = 70000 if CFG["kind"] == "car" else (50000 if CFG["kind"] == "bike" else 600000)
WHEEL_BUDGET = 5000
MAX_TEX = 2048
MAX_NORMAL_TEX = 1024   # normal maps of small details (lights, leather): 1K is plenty
os.makedirs(os.path.join(OUT, "Textures"), exist_ok=True)
REPORT = {"key": KEY, "kind": CFG["kind"], "steps": []}


def log(*a):
    msg = " ".join(str(x) for x in a)
    REPORT["steps"].append(msg)
    print("M80", msg)


def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == "MESH" else 0


def world_bbox(o):
    co = np.array([v.co for v in o.data.vertices]) if len(o.data.vertices) else np.zeros((1, 3))
    m = np.array(o.matrix_world)
    w = co @ m[:3, :3].T + m[:3, 3]
    return w.min(0), w.max(0)


# Images linked from another disk (the old E:\BitBucket copy): look for them on D: or by name.
IMAGE_ROOTS = [r"D:\BitBucket\mazzareththegame\Assets", r"D:\Blender\AssetsMazzarethTheGame"]


def relink_images():
    index = None
    fixed = missing = 0
    for im in bpy.data.images:
        if im.packed_file or im.source != "FILE" or not im.filepath:
            continue
        path = bpy.path.abspath(im.filepath)
        if os.path.exists(path):
            continue
        cand = None
        if len(path) > 2 and path[1] == ":":
            alt = "D" + path[1:]
            if os.path.exists(alt):
                cand = alt
        if not cand:
            if index is None:
                index = {}
                for root in IMAGE_ROOTS:
                    for dirpath, _, files in os.walk(root):
                        for f in files:
                            index.setdefault(f.lower(), os.path.join(dirpath, f))
            cand = index.get(os.path.basename(path).lower())
        if cand:
            im.filepath = cand
            im.reload()
            fixed += 1
        else:
            missing += 1
    log("images relinked", fixed, "still missing", missing)


# ---------------------------------------------------------------------------------------------
# 1) Keep what is visible, as plain meshes

def collect():
    scene = bpy.context.scene
    view = bpy.context.view_layer
    # Instanced collections become real objects first.
    for o in list(scene.objects):
        if o.type == "EMPTY" and o.instance_type == "COLLECTION" and o.instance_collection and o.visible_get():
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            view.objects.active = o
            bpy.ops.object.duplicates_make_real()
    keep = [o for o in scene.objects if o.type in ("MESH", "CURVE", "FONT", "SURFACE", "META") and o.visible_get() and not o.hide_render]
    for o in keep:
        if o.type != "MESH":
            continue
        base = tri_count(o)
        for m in o.modifiers:
            if m.type == "SUBSURF":
                lv = 0 if base > 20000 else 1
                m.levels = min(m.levels, lv)
                m.render_levels = min(m.render_levels, lv)
            if not m.show_render:
                m.show_viewport = False
    # Evaluated copies (modifiers applied, curves and text as meshes), in world space, no parents.
    dg = bpy.context.evaluated_depsgraph_get()
    meshes = []
    for o in keep:
        try:
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        except Exception as e:  # noqa: BLE001
            log("skip", o.name, e)
            continue
        if not me or len(me.polygons) == 0:
            continue
        me.transform(o.matrix_world)
        a = me.attributes.new("m80_src", "INT", "FACE")
        a.data.foreach_set("value", [len(meshes)] * len(me.polygons))
        n = bpy.data.objects.new("M80_" + o.name, me)
        bpy.context.scene.collection.objects.link(n)
        meshes.append(n)
    keep_names = {o.name for o in meshes}
    for o in list(bpy.data.objects):
        if o.name not in keep_names:
            bpy.data.objects.remove(o, do_unlink=True)
    log("visible meshes", len(meshes), "triangles", sum(tri_count(o) for o in meshes))
    return meshes


def drop_scenery_and_duplicates(meshes):
    sizes = []
    info = []
    for o in meshes:
        lo, hi = world_bbox(o)
        info.append((o, lo, hi, tri_count(o)))
        sizes.append(float(np.max(hi - lo)))
    med = float(np.median(sizes)) if sizes else 1.0
    # Lowest point of the real (non flat) geometry: ground planes lie at or under it.
    solid = [lo[2] for o, lo, hi, t in info if (hi - lo)[2] > 0.02 * max((hi - lo)[0], (hi - lo)[1], 1e-6)]
    zmin = min(solid) if solid else 0.0
    out = []
    seen = {}
    for o, lo, hi, t in info:
        ext = hi - lo
        flat = ext[2] < 0.02 * max(ext[0], ext[1], 1e-6)
        ground = flat and t <= 400 and hi[2] <= zmin + 0.02 * float(max(ext)) and float(max(ext[0], ext[1])) > 2 * med
        sky = t <= 64 and float(max(ext)) > 5 * med
        if ground or sky:
            log("drop scenery", o.name, [round(float(v), 2) for v in ext], t)
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        key = (t, tuple(np.round(lo, 3)), tuple(np.round(hi, 3)))
        if t > 0 and key in seen:
            log("drop duplicate", o.name, "=", seen[key])
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        seen[key] = o.name
        out.append(o)
    return out


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name
    o.data.name = name
    return o


def separate_loose(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    return list(bpy.context.selected_objects)


# ---------------------------------------------------------------------------------------------
# 2) Wheels

def split_by_source(o):
    """Splits a joined mesh back into the source objects (by the M80 source index attribute)."""
    if not o.data.attributes.get("m80_src"):
        return [o]
    attr = o.data.attributes["m80_src"]
    vals = np.zeros(len(o.data.polygons), dtype=np.int32)
    attr.data.foreach_get("value", vals)
    out = []
    for v in np.unique(vals):
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.faces.ensure_lookup_table()
        kill = [f for f in bm.faces if vals[f.index] != v]
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        me = bpy.data.meshes.new("src%d" % v)
        bm.to_mesh(me)
        bm.free()
        for m in o.data.materials:
            me.materials.append(m)
        n = bpy.data.objects.new("src%d" % v, me)
        bpy.context.scene.collection.objects.link(n)
        out.append(n)
    bpy.data.objects.remove(o, do_unlink=True)
    return out


def find_wheels(parts, count):
    """Ground-touching round parts are the tyres; returns [(centre, radius, width, axle_axis)]."""
    boxes = [(p,) + world_bbox(p) for p in parts]
    cand = []
    for p, lo, hi in boxes:
        ext = hi - lo
        # round in a vertical plane: height ~ one horizontal extent, the other one thinner
        h = float(ext[2])
        a, b = float(ext[0]), float(ext[1])
        for axle, d_along, d_across in ((1, b, a), (0, a, b)):
            if h > 0 and abs(d_across - h) < 0.12 * h and 0.12 * h < d_along < 0.8 * h:   # a tyre has some width
                cand.append((p, (lo + hi) / 2, h / 2, d_along, axle, tri_count(p)))
                break
    if os.environ.get("M80_DEBUG"):
        rb = sorted(((float(np.max(hi - lo)), p.name, [round(float(x), 3) for x in lo], [round(float(x), 3) for x in hi - lo]) for p, lo, hi in boxes), reverse=True)
        for r in rb[:25]:
            log("part", r)
        for c in sorted(cand, key=lambda c: -c[2])[:20]:
            log("round", c[0].name, round(float(c[2]), 3), [round(float(x), 3) for x in c[1]])
    if len(cand) < count:
        return None
    # The tyres: the biggest set of `count` round parts with the same radius, standing at the same
    # height, apart from each other (doors or lamps can be round too, but not four alike on the ground).
    height = max(float(hi[2]) for _, lo, hi in boxes) - min(float(lo[2]) for _, lo, hi in boxes)
    cand.sort(key=lambda c: -c[2])
    chosen = None
    groups = []
    for seed in cand:
        r0, b0 = seed[2], float(seed[1][2] - seed[2])
        if r0 < 0.12 * height:
            break
        group = []
        for c in cand:
            if abs(c[2] - r0) <= 0.1 * r0 and abs(float(c[1][2] - c[2]) - b0) <= 0.15 * r0 and                     all(np.linalg.norm(c[1][:2] - k[1][:2]) > 1.2 * r0 for k in group):
                group.append(c)
        if len(group) >= count:
            groups.append(group[:count])
    # Of the possible sets, the one touching the ground (lowest), then the biggest.
    if groups:
        chosen = min(groups, key=lambda g: (round(min(float(c[1][2] - c[2]) for c in g) / (0.1 * g[0][2])), -g[0][2]))
    if not chosen:
        log("no set of %d alike round parts on the ground" % count)
        return None
    return [(c[1], c[2], c[3], c[4]) for c in chosen]


def straighten(o):
    """Turns the vehicle about Z so its long side lies along X or Y (some scenes have it at an angle)."""
    co = np.array([v.co for v in o.data.vertices])[:, :2]
    if len(co) < 10:
        return
    c = co.mean(0)
    w, v = np.linalg.eigh(np.cov((co - c).T))
    major = v[:, int(np.argmax(w))]
    ang = math.atan2(major[1], major[0])
    # Snap to the nearest axis: only the leftover angle is removed.
    snap = round(ang / (math.pi / 2)) * (math.pi / 2)
    delta = ang - snap
    if abs(delta) < math.radians(0.5):
        return
    o.data.transform(Matrix.Translation(Vector((c[0], c[1], 0))) @ Matrix.Rotation(-delta, 4, "Z") @ Matrix.Translation(Vector((-c[0], -c[1], 0))))
    o.data.update()
    log("straightened by", round(math.degrees(delta), 1), "degrees")


def build_vehicle(meshes):
    count = 4 if CFG["kind"] == "car" else 2
    # Tyres made of many loose pieces: look at whole objects first, after straightening them all.
    body = join(meshes, "Body")
    straighten(body)
    parts = separate_loose(body)
    log("loose parts", len(parts))
    wheels = find_wheels(parts, count)
    if not wheels and len(meshes) > 1:
        log("no round tyre among the loose parts: trying the source objects")
        whole = join(parts, "Body")
        groups = split_by_source(whole)
        wheels = find_wheels(groups, count)
        whole = join(groups, "Body")
        parts = separate_loose(whole)
    if not wheels:
        if CFG["kind"] == "bike":
            return None, None
        raise RuntimeError("wheels not found")
    axle = wheels[0][3]                 # 1: wheels turn about Y (car along X), 0: about X (car along Y)
    length_axis = 0 if axle == 1 else 1
    centres = np.array([w[0] for w in wheels])
    # Parts inside a wheel's cylinder go with that wheel (rim, hubcap, brake, nuts...).
    groups = {i: [] for i in range(len(wheels))}
    body_parts = []
    ground0 = min(float(w[0][2] - w[1]) for w in wheels)
    r_min = min(w[1] for w in wheels)
    for p in parts:
        lo, hi = world_bbox(p)
        c = (lo + hi) / 2
        ext = hi - lo
        owner = None
        for i, (wc, r, wd, ax) in enumerate(wheels):
            d_plane = math.hypot(c[length_axis] - wc[length_axis], c[2] - wc[2])
            d_axle = abs(c[axle] - wc[axle])
            if d_plane + 0.5 * max(ext[length_axis], ext[2]) <= 1.08 * r and d_axle <= 1.6 * wd + 0.02:
                owner = i
                break
        if owner is None and float(lo[2]) < ground0 - 0.1 * r_min:
            log("drop part under the ground", p.name, [round(float(x), 3) for x in lo])
            bpy.data.objects.remove(p, do_unlink=True)
            continue
        (groups[owner] if owner is not None else body_parts).append(p)
    log("wheel parts", [len(groups[i]) for i in groups], "body parts", len(body_parts))
    body = join(body_parts, "Body")
    wheel_objs = [join(groups[i], "Wheel%d" % i) for i in range(len(wheels))]
    # Scale to the real length, then orientation and placement.
    lo, hi = world_bbox(body)
    s = CFG["length"] / float(hi[length_axis] - lo[length_axis])
    allo = [body] + wheel_objs
    rot = Matrix.Identity(4) if length_axis == 0 else Matrix.Rotation(-math.pi / 2, 4, "Z")
    mid = Vector(((centres[:, 0].min() + centres[:, 0].max()) / 2, (centres[:, 1].min() + centres[:, 1].max()) / 2, 0))
    front = CFG.get("front", 0) or front_sign(body, length_axis, mid[length_axis])
    if front < 0:
        rot = Matrix.Rotation(math.pi, 4, "Z") @ rot
    ground = min(float(world_bbox(w)[0][2]) for w in wheel_objs)
    mid.z = ground
    xf = Matrix.Scale(s, 4) @ rot @ Matrix.Translation(-mid)
    for o in allo:
        o.data.transform(xf)
        o.data.update()
    log("scale", round(s, 4), "length axis", "XY"[length_axis], "front sign", front)
    # Name the wheels by corner (front = +X, left = +Y).
    named = {}
    for o in wheel_objs:
        lo, hi = world_bbox(o)
        c = (lo + hi) / 2
        name = ("F" if c[0] > 0 else "R") + ("L" if c[1] > 0 else "R")
        if CFG["kind"] == "bike":
            name = "F" if c[0] > 0 else "R"
        named[name] = (o, Vector(c), float(hi[2] - lo[2]) / 2, float(hi[1] - lo[1]))
    return body, named


def front_sign(body, length_axis, centre):
    """+1 if the front is towards +length axis: white/front lights there, red/rear lights the other way."""
    me = body.data
    mats = [m.name.lower() if m else "" for m in me.materials]
    front_kw = re.compile(r"white|bianc|anterior|front|head|faro|fanale_ant|luce_b")
    rear_kw = re.compile(r"red|ross|posterior|rear|tail|stop|luci ?post|luce_r")
    score = 0.0
    co = np.array([v.co for v in me.vertices])
    for p in me.polygons:
        n = mats[p.material_index] if p.material_index < len(mats) else ""
        if not n:
            continue
        sgn = 1 if front_kw.search(n) else (-1 if rear_kw.search(n) else 0)
        if sgn:
            score += sgn * float(np.sign(co[p.vertices[0]][length_axis] - centre))
    # Also the lights' object names were lost in the join: fall back on the score only.
    return -1 if score < 0 else 1


# ---------------------------------------------------------------------------------------------
# 3) Triangle budget

def decimate(o, budget):
    t = tri_count(o)
    if t <= budget:
        return t
    m = o.modifiers.new("M80Dec", "DECIMATE")
    m.decimate_type = "COLLAPSE"
    m.ratio = max(0.02, budget / t)
    m.use_collapse_triangulate = True
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)
    log("decimate", o.name, t, "->", tri_count(o))
    return tri_count(o)


# ---------------------------------------------------------------------------------------------
# 4) Materials and textures

def clean(name):
    return re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")[:48] or "Mat"


def linked_image(sock, depth=0):
    if not sock.is_linked or depth > 6:
        return None
    n = sock.links[0].from_node
    if n.type == "TEX_IMAGE" and n.image:
        return n.image
    for s in n.inputs:
        if s.type in ("RGBA", "VECTOR", "VALUE") and s.is_linked:
            im = linked_image(s, depth + 1)
            if im:
                return im
    return None


def linked_colour(sock, depth=0):
    """A representative colour for a procedural input (ramp mid, RGB node, mix inputs)."""
    if not sock.is_linked or depth > 6:
        v = sock.default_value
        return list(v[:3]) if hasattr(v, "__len__") else None
    n = sock.links[0].from_node
    if n.type == "RGB":
        return list(n.outputs[0].default_value[:3])
    if n.type == "VALTORGB":
        els = n.color_ramp.elements
        c = np.mean([list(e.color[:3]) for e in els], axis=0)
        return [float(x) for x in c]
    for s in n.inputs:
        if s.type == "RGBA":
            c = linked_colour(s, depth + 1)
            if c:
                return c
    return None


def principled(mat):
    if not (mat.use_nodes and mat.node_tree):
        return None
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    for n in mat.node_tree.nodes:   # inside a group
        if n.type == "GROUP" and n.node_tree:
            for g in n.node_tree.nodes:
                if g.type == "BSDF_PRINCIPLED":
                    return g
    return None


SAVED = {}


def save_image(im, normal=False):
    if im is None:
        return None
    base = re.sub(r"\.\d{3}$", "", im.name)
    base = clean(os.path.splitext(base)[0])
    if base in SAVED:
        return SAVED[base]
    try:
        if im.size[0] == 0:
            im.reload()
        if im.size[0] == 0:
            return None
        w, h = im.size
        limit = MAX_NORMAL_TEX if normal else MAX_TEX
        if max(w, h) > limit:
            k = limit / max(w, h)
            im.scale(max(1, int(w * k)), max(1, int(h * k)))
        path = os.path.join(OUT, "Textures", "T_%s_%s.png" % (KEY, base))
        im.file_format = "PNG"
        im.save(filepath=path)
    except Exception as e:  # noqa: BLE001
        log("image failed", im.name, e)
        return None
    SAVED[base] = os.path.basename(path)
    return SAVED[base]


def classify(name, glass, emit):
    n = name.lower()
    if glass or re.search(r"glass|vetr|crystal|cristal|polycarb|lunott|window|finestrin", n):
        return "glass"
    if re.search(r"carlight|light|luce|luci|lamp|fanal|faro|stop", n) or emit:
        return "light"
    if re.search(r"tire|tyre|gomma|rubber|pneu|gum", n):
        return "rubber"
    if re.search(r"paint|vernic|carrozz|body|auto|blue|gloss|coated|car ", n):
        return "paint"
    if re.search(r"chrom|crom|steel|metal|acciaio|brushed|alumin|nickel", n):
        return "metal"
    return "generic"


def export_materials(objs):
    mats = {}
    for o in objs:
        for s in o.material_slots:
            m = s.material
            if not m or m.name in mats:
                continue
            p = principled(m)
            d = {"slot": clean(m.name), "color": list(m.diffuse_color[:3]), "metallic": float(m.metallic), "roughness": float(m.roughness),
                 "opacity": 1.0, "emissive": [0, 0, 0], "base_tex": None, "normal_tex": None}
            glass = False
            emit = False
            if p:
                bc = p.inputs.get("Base Color")
                d["base_tex"] = save_image(linked_image(bc)) if bc else None
                c = linked_colour(bc) if bc else None
                if c:
                    d["color"] = c
                for key, out in (("Metallic", "metallic"), ("Roughness", "roughness")):
                    s_ = p.inputs.get(key)
                    if s_ is not None and not s_.is_linked:
                        d[out] = float(s_.default_value)
                tr = p.inputs.get("Transmission Weight") or p.inputs.get("Transmission")
                al = p.inputs.get("Alpha")
                if tr is not None and not tr.is_linked and tr.default_value > 0.5:
                    glass = True
                if al is not None and not al.is_linked and al.default_value < 0.6:
                    glass = True
                    d["opacity"] = float(al.default_value)
                es = p.inputs.get("Emission Strength")
                ec = p.inputs.get("Emission Color") or p.inputs.get("Emission")
                if es is not None and ec is not None and es.default_value > 0.01:
                    col = list(ec.default_value[:3]) if not ec.is_linked else d["color"]
                    if max(col) > 0.01:
                        emit = True
                        d["emissive"] = [float(x) * min(es.default_value, 10.0) for x in col]
                nm = p.inputs.get("Normal")
                if nm is not None and nm.is_linked:
                    d["normal_tex"] = save_image(linked_image(nm), normal=True)
            d["type"] = classify(m.name, glass, emit)
            mats[m.name] = d
    return mats


# ---------------------------------------------------------------------------------------------
# 5) Skeleton and export

def make_rig(body, wheels):
    arm_data = bpy.data.armatures.new("Armature")
    arm = bpy.data.objects.new("Armature", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    root = arm_data.edit_bones.new("Root")
    root.head = (0, 0, 0)
    root.tail = (0, 30.0, 0)
    for name, (o, c, r, w) in wheels.items():
        b = arm_data.edit_bones.new("Wheel_" + name)
        b.head = c
        b.tail = c + Vector((0, 15.0, 0))
        b.parent = root
    bpy.ops.object.mode_set(mode="OBJECT")
    def bind(o, bone):
        vg = o.vertex_groups.new(name=bone)
        vg.add(range(len(o.data.vertices)), 1.0, "REPLACE")
        o.parent = arm
        md = o.modifiers.new("Armature", "ARMATURE")
        md.object = arm
    bind(body, "Root")
    for name, (o, c, r, w) in wheels.items():
        bind(o, "Wheel_" + name)
    return arm


def to_centimetres(objs, wheels):
    """Rigged export in centimetres (scene unit 0.01): otherwise the FBX root bone gets a x100 scale in Unreal and
    Chaos, which divides the wheel positions by the root body's scale, sees every wheel at the centre."""
    sc = Matrix.Scale(100.0, 4)
    for o in objs:
        o.data.transform(sc @ o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.01
    return {k: (o, c * 100.0, r * 100.0, w * 100.0) for k, (o, c, r, w) in wheels.items()}


def export(objs, arm=None, name=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    if arm:
        arm.select_set(True)
    path = os.path.join(OUT, (name or KEY) + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"} if arm else {"MESH"},
                             axis_forward="-Y", axis_up="Z", apply_unit_scale=True, mesh_smooth_type="FACE",
                             add_leaf_bones=False, bake_anim=False, use_armature_deform_only=True,
                             primary_bone_axis="Y", secondary_bone_axis="X", path_mode="STRIP")
    log("exported", path)


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True
    try:
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    except Exception:  # noqa: BLE001
        pass


def main():
    relink_images()
    meshes = drop_scenery_and_duplicates(collect())
    body = wheels = None
    if CFG["kind"] in ("car", "bike"):
        body, wheels = build_vehicle(meshes)
        if body is None:
            # Bike without recognisable wheels: one static mesh at its real length.
            meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
            body = join(meshes, KEY)
            lo, hi = world_bbox(body)
            ax = 0 if (hi - lo)[0] >= (hi - lo)[1] else 1
            s = CFG["length"] / float((hi - lo)[ax])
            mid = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
            rot = Matrix.Identity(4) if ax == 0 else Matrix.Rotation(-math.pi / 2, 4, "Z")
            body.data.transform(Matrix.Scale(s, 4) @ rot @ Matrix.Translation(-mid))
            log("bike without wheels: static, scale", round(s, 4))
            CFG["kind"] = "static"
    if wheels:
        decimate(body, BODY_BUDGET)
        for name, (o, c, r, w) in wheels.items():
            o.name = o.data.name = "Tyre_" + name
            decimate(o, WHEEL_BUDGET)
        objs = [body] + [v[0] for v in wheels.values()]
        REPORT["wheels"] = {k: {"centre_cm": [round(float(x) * 100, 1) for x in v[1]], "radius_cm": round(v[2] * 100, 1),
                                "width_cm": round(v[3] * 100, 1)} for k, v in wheels.items()}
        lo, hi = world_bbox(body)
        REPORT["body_box_cm"] = [round(float(x) * 100, 1) for x in list(lo) + list(hi)]
        REPORT["materials"] = export_materials(objs)
        for o in objs:
            smooth(o)
        # Cars and two-wheelers alike: skeleton Root + Wheel_XX, drivable in the game.
        export(objs, make_rig(body, to_centimetres(objs, wheels)))
    elif CFG["kind"] == "static":
        decimate(body, BODY_BUDGET)
        REPORT["materials"] = export_materials([body])
        smooth(body)
        export([body])
    else:
        # Parts listed in "split" become meshes of their own (placed relative to the main one).
        pieces = {}
        for part in CFG.get("split", []):
            sel = [o for o in meshes if o.name.startswith("M80_" + part)]
            if sel:
                pieces[part] = join(sel, KEY + "_" + part)
                meshes = [o for o in meshes if o not in sel]
        body = join(meshes, KEY)
        lo, hi = world_bbox(body)
        mid = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
        sc = CFG.get("scale", 1.0)
        body.data.transform(Matrix.Scale(sc, 4) @ Matrix.Translation(-mid))
        decimate(body, BODY_BUDGET)
        lo, hi = world_bbox(body)
        REPORT["box_cm"] = [round(float(x) * 100, 1) for x in list(lo) + list(hi)]
        mats = export_materials([body] + list(pieces.values()))
        REPORT["materials"] = mats
        smooth(body)
        export([body])
        REPORT["pieces"] = {}
        for part, o in pieces.items():
            plo, phi = world_bbox(o)
            pmid = Vector(((plo[0] + phi[0]) / 2, (plo[1] + phi[1]) / 2, plo[2]))
            o.data.transform(Matrix.Scale(sc, 4) @ Matrix.Translation(-pmid))
            smooth(o)
            export([o], name=KEY + "_" + part)
            # where to put it so it stands where it was, relative to the main mesh (cm)
            REPORT["pieces"][part] = {"offset_cm": [round(float(x) * 100 * sc, 1) for x in (pmid - mid)], "triangles": tri_count(o)}
    REPORT["triangles"] = {o.name: tri_count(o) for o in bpy.context.scene.objects if o.type == "MESH"}
    REPORT["textures"] = sorted(SAVED.values())
    with open(os.path.join(OUT, KEY + ".json"), "w", encoding="utf-8") as f:
        json.dump(REPORT, f, indent=1)
    log("done")


main()
