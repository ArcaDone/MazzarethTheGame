"""Blender 5.2: the objects people carry or use in the crowd test (1980s Sicily), one FBX each, ready for Unreal.

- Downloaded (Sketchfab, D:/BlenderTest/Folla/sketchfab/<folder>, see README "Fonti e licenze"): brought to real size
  (their files come in cm, m or arbitrary units), the parts not needed left out (the shawl's mannequin, the umbrella
  stand), textures cut to MAX_PX and written next to the FBX.
- Made here (nothing suitable found): flat caps (coppola) in three cloths, an old lady's black handbag, prescription
  glasses with a thick tortoiseshell frame, a leather briefcase, a folded newspaper. Their textures (tartan, tweed,
  felt, leather, newsprint) are drawn with numpy, tiling in metres through a cube projection.
Every object: one mesh SM_M80_<Key>, triangulated, metres in Blender -> cm in the FBX, origin at the bottom centre
(the ground or the hand under it), front along -Y as the other props.

Run: blender -b --factory-startup --python m80_folla_oggetti.py -- [Key,Key...]
Out: Saved/Mazzarino80/Folla/Oggetti/<Key>/{SM_M80_<Key>.fbx, Textures/, <Key>.json}, anteprima.png per object.
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

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.join(ROOT, "Saved", "Mazzarino80", "Folla", "Oggetti")
SKETCHFAB = "D:/BlenderTest/Folla/sketchfab"
MAX_PX = 1024
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = [k for k in (ARGS[0].split(",") if ARGS else []) if k]

UMBRELLAS = "simple_umbrellas_and_a_classic_umbrella_stand"
# size: (axis, metres) the model is scaled to: "z" its height, "max" its longest side.
DOWNLOADED = {
    "Bastone": {"src": "low_poly_walking_stick", "size": ("z", 0.90)},
    "Radiolina": {"src": "radio_transistor", "size": ("max", 0.22)},
    "OcchialiSole": {"src": "sunglasses", "size": ("max", 0.145)},
    "SuperSantos": {"src": "super_santos", "size": ("max", 0.22)},
    "Retina": {"src": "net-bag", "file": "source/Net_Bag/Net_Bag/SM_Net_Bag.fbx", "size": ("max", 0.55)},
    "OmbrelloChiuso": {"src": UMBRELLAS, "keep": r"^classic_umbrela_closed_paraigues", "size": ("max", 0.92)},
    "OmbrelloAperto": {"src": UMBRELLAS, "keep": r"^classic_umbrela_opened_paraigues", "size": ("max", 1.05)},
    "Bicicletta": {"src": "low-poly-vintage-bicycle-model-too-much-low-poly", "size": ("max", 1.75)},
    "Scialle": {"src": "shawl-_chiffon_5", "keep": r"Default", "size": ("z", 0.62)},
}


# --- helpers -------------------------------------------------------------------------------------------------------

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def image(name, rgb, rough=None):
    """A texture from an HxWx3 float array (0-1)."""
    h, w, _ = rgb.shape
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), dtype=np.float32)
    px[..., :3] = np.clip(rgb, 0, 1)
    img.pixels.foreach_set(px.ravel())
    return img


def material(name, img=None, color=(0.5, 0.5, 0.5), rough=0.8, metal=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
    if img is not None:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def noise(h, w, scale, rng):
    """Smooth value noise in 0-1 (bilinear upsampling of a coarse random grid), tiling."""
    gh, gw = max(2, h // scale), max(2, w // scale)
    g = rng.random((gh, gw))
    y = np.linspace(0, gh, h, endpoint=False)
    x = np.linspace(0, gw, w, endpoint=False)
    y0, x0 = np.floor(y).astype(int), np.floor(x).astype(int)
    fy, fx = (y - y0)[:, None], (x - x0)[None, :]
    a = g[y0 % gh][:, x0 % gw]
    b = g[y0 % gh][:, (x0 + 1) % gw]
    c = g[(y0 + 1) % gh][:, x0 % gw]
    d = g[(y0 + 1) % gh][:, (x0 + 1) % gw]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy


def tartan(n, base, lines, rng):
    """Checked cloth: crossing bands (offset, width, colour) on a base colour, with a twill grain."""
    rgb = np.ones((n, n, 3)) * np.array(base)
    idx = np.arange(n)
    for off, width, col, strength in lines:
        band = ((idx - off * n) % n) < width * n
        col = np.array(col)
        rgb[band, :, :] = rgb[band, :, :] * (1 - strength) + col * strength
        rgb[:, band, :] = rgb[:, band, :] * (1 - strength) + col * strength
    twill = ((idx[:, None] + idx[None, :]) % 4 < 2) * 0.06
    return rgb * (1 - twill[..., None]) * (0.92 + 0.16 * noise(n, n, 16, rng)[..., None])


def tweed(n, colours, rng):
    """Flecked wool: random fibres of a few colours over a mottled base, herringbone ribs."""
    base = np.array(colours[0]) * (0.8 + 0.4 * noise(n, n, 24, rng)[..., None])
    pick = rng.random((n, n))
    for i, col in enumerate(colours[1:]):
        fleck = (pick > 1 - 0.08 * (i + 1)) & (pick <= 1 - 0.08 * i)
        base[fleck] = np.array(col)
    idx = np.arange(n)
    rib = (((idx[:, None] // 6) % 2) * 2 - 1) * idx[None, :] + idx[:, None]
    base *= (0.9 + 0.1 * ((rib % 8) < 4))[..., None]
    return base


def leather(n, col, rng):
    grain = noise(n, n, 6, rng) * 0.6 + noise(n, n, 40, rng) * 0.4
    return np.array(col) * (0.75 + 0.5 * grain[..., None])


def newsprint(w, h, rng):
    """A folded newspaper's front: masthead, a headline, a photo block, columns of grey text lines."""
    rgb = np.ones((h, w, 3)) * np.array([0.86, 0.84, 0.78])
    rgb[int(h * 0.04):int(h * 0.13), int(w * 0.08):int(w * 0.92)] = 0.12          # masthead
    rgb[int(h * 0.16):int(h * 0.21), int(w * 0.06):int(w * 0.94)] = 0.25          # headline
    y0, y1, x0, x1 = int(h * 0.25), int(h * 0.55), int(w * 0.06), int(w * 0.55)
    rgb[y0:y1, x0:x1] = 0.35 + 0.3 * noise(y1 - y0, x1 - x0, 20, rng)[..., None]   # the photo
    cols = [(0.06, 0.30), (0.33, 0.62), (0.65, 0.94)]
    for c0, c1 in cols:
        for row in range(int(h * 0.25), int(h * 0.97), 7):
            if c0 < 0.55 and row < h * 0.57 and c1 <= 0.62:
                continue
            length = int((c1 - c0) * w * (0.75 + 0.25 * rng.random()))
            rgb[row:row + 3, int(c0 * w):int(c0 * w) + length] = 0.35
    return rgb


def finish(objs, key, fit=None, keep_origin=False):
    """Join, size, put the origin at the bottom centre, triangulate; returns the single mesh object."""
    bpy.ops.object.select_all(action="DESELECT")
    # Each piece goes into a fresh object with its world transform baked into the mesh: an imported object can carry
    # an animation or other FBX leftovers (the net bag kept its 0.001 scale into the exported FBX).
    fresh = []
    for o in objs:
        if o.data.shape_keys:   # Mesh.transform leaves shape keys alone, and the basis is what gets exported
            o.shape_key_clear()
        me = o.data.copy()
        me.transform(o.matrix_world)
        n = bpy.data.objects.new(o.name, me)
        bpy.context.scene.collection.objects.link(n)
        bpy.data.objects.remove(o)
        n.select_set(True)
        fresh.append(n)
    objs = fresh
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = "SM_M80_" + key
    co = np.array([v.co[:] for v in ob.data.vertices])
    lo, hi = co.min(0), co.max(0)
    if fit:
        axis, metres = fit
        size = hi[2] - lo[2] if axis == "z" else (hi - lo).max()
        s = metres / size
        ob.data.transform(Matrix.Scale(s, 4))
        lo, hi = lo * s, hi * s
    if not keep_origin:
        ob.data.transform(Matrix.Translation(Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def export(ob, key, extra):
    out = os.path.join(OUT, key)
    tex_dir = os.path.join(out, "Textures")
    os.makedirs(tex_dir, exist_ok=True)
    # Every image the mesh uses written next to the FBX, at most MAX_PX (Unreal imports them from there).
    for m in ob.data.materials:
        if not m or not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            img = getattr(n, "image", None)
            if n.type != "TEX_IMAGE" or img is None or img.size[0] == 0:
                continue
            w, h = img.size
            s = min(1.0, MAX_PX / max(w, h))
            if s < 1:
                img.scale(max(1, int(w * s)), max(1, int(h * s)))
            name = re.sub(r"[^A-Za-z0-9_]", "_", "T_M80_%s_%s" % (key, img.name.rsplit(".", 1)[0]))
            path = os.path.join(tex_dir, name + ".png")
            img.filepath_raw = path
            img.file_format = "PNG"
            img.save()
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    fbx = os.path.join(out, "SM_M80_%s.fbx" % key)
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="FACE",
                             bake_space_transform=True, path_mode="COPY", embed_textures=False)
    co = np.array([v.co[:] for v in ob.data.vertices])
    info = {"key": key, "triangles": len(ob.data.polygons), "size_m": [round(float(x), 3) for x in co.max(0) - co.min(0)],
            "materials": [m.name for m in ob.data.materials if m]}
    info.update(extra)
    with open(os.path.join(out, key + ".json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    preview(ob, os.path.join(out, "anteprima.png"))
    return info


def preview(ob, path):
    co = np.array([v.co[:] for v in ob.data.vertices])
    lo, hi = co.min(0), co.max(0)
    centre = Vector(((lo + hi) / 2).tolist())
    r = float(np.linalg.norm(hi - lo)) * 0.5 + 1e-3
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    bpy.context.scene.collection.objects.link(cam)
    cam.location = centre + Vector((r * 1.6, -r * 2.2, r * 1.2))
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(30))
    bpy.context.scene.collection.objects.link(sun)
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = 600
    sc.render.filepath = path
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.55, 0.55, 0.58)
    bpy.ops.render.render(write_still=True)


# --- downloaded models ---------------------------------------------------------------------------------------------

def downloaded(key, cfg):
    reset()
    folder = os.path.join(SKETCHFAB, cfg["src"])
    src = os.path.join(folder, cfg["file"]) if "file" in cfg else next(
        os.path.join(d, f) for d, _, fs in os.walk(folder) for f in fs if f.lower().endswith((".gltf", ".glb", ".fbx")))
    if src.lower().endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=src)
    else:
        bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if "keep" in cfg:
        for o in meshes:
            if not re.search(cfg["keep"], o.name):
                bpy.data.objects.remove(o)
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    # Parents (glTF empties) carry the file's scale: bake world matrices into the meshes, then drop them.
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o)
    # The net bag's FBX keeps its textures apart: hook them up.
    if key == "Retina":
        tex = os.path.join(folder, "textures", "T_Net_Bag_BC.png")
        m = material("M_Net_Bag", bpy.data.images.load(tex), rough=0.7)
        for o in meshes:
            o.data.materials.clear()
            o.data.materials.append(m)
    ob = finish(meshes, key, cfg["size"])
    return export(ob, key, {"source": src})


# --- made here -----------------------------------------------------------------------------------------------------

def cube_uv(ob, size_m):
    """Cube projection, one texture repeat every size_m metres."""
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=size_m, correct_aspect=False, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def coppola(key, make_cloth):
    """Flat cap: a low crown sloping forward over a short stiff peak (about 21 x 19 cm, 7 cm high)."""
    reset()
    cloth = make_cloth()   # after the reset, which empties the file
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0)
    crown = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(crown.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    for v in bm.verts:
        x, y, z = v.co
        # Lower and longer at the front: the crown leans forward and covers the peak's root.
        v.co = Vector((x * 0.105 + z * 0.035, y * 0.096, z * (0.055 + 0.02 * max(0.0, -x))))
    bm.to_mesh(crown.data)
    bm.free()
    solid = crown.modifiers.new("s", "SOLIDIFY")
    solid.thickness = 0.003
    bpy.ops.object.modifier_apply(modifier="s")
    # Peak: half an ellipse from inside the crown's front edge (x 0.105) out to 6 cm beyond it, tipped down a little
    # (-Y is the front of every prop: the cap is made facing +X and turned at the end).
    me = bpy.data.meshes.new("peak")
    bm = bmesh.new()
    rim = []
    for i in range(25):
        t = math.radians(-90 + 180 * i / 24)
        x = 0.06 + 0.105 * math.cos(t)
        rim.append(bm.verts.new((x, 0.088 * math.sin(t), 0.004 - 0.12 * max(0.0, x - 0.105))))
    bm.faces.new(rim)
    bm.to_mesh(me)
    bm.free()
    peak = bpy.data.objects.new("peak", me)
    bpy.context.scene.collection.objects.link(peak)
    bpy.context.view_layer.objects.active = peak
    solid = peak.modifiers.new("s", "SOLIDIFY")
    solid.thickness = 0.005
    bpy.ops.object.modifier_apply(modifier="s")
    for o in (crown, peak):
        o.data.materials.append(cloth)
    bpy.ops.object.select_all(action="DESELECT")
    ob = finish([crown, peak], key)
    ob.data.transform(Matrix.Rotation(math.radians(-90), 4, "Z"))   # front from +X to -Y
    cube_uv(ob, 0.12)
    return export(ob, key, {"made": "flat cap"})


def borsetta():
    """An old lady's black leather handbag: trapezoid body with a front flap, gilt clasp, one arched handle."""
    reset()
    rng = np.random.default_rng(3)
    skin = material("M80_Borsetta_Pelle", image("borsetta_pelle", leather(512, (0.035, 0.033, 0.03), rng)), rough=0.45)
    gilt = material("M80_Borsetta_Ottone", color=(0.75, 0.6, 0.3), rough=0.3, metal=1.0)
    bpy.ops.mesh.primitive_cube_add(size=1)
    body = bpy.context.active_object
    body.scale = (0.26, 0.085, 0.19)
    bpy.ops.object.transform_apply(scale=True)
    for v in body.data.vertices:
        if v.co.z > 0:
            v.co.x *= 0.82
            v.co.y *= 0.7
    bev = body.modifiers.new("b", "BEVEL")
    bev.width, bev.segments = 0.012, 3
    bpy.ops.object.modifier_apply(modifier="b")
    body.location.z = 0.095
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.034, 0.15))
    flap = bpy.context.active_object
    flap.scale = (0.22, 0.006, 0.09)
    flap.rotation_euler.x = math.radians(-8)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.012, depth=0.01, location=(0, -0.042, 0.115),
                                        rotation=(math.radians(90), 0, 0))
    clasp = bpy.context.active_object
    bpy.ops.mesh.primitive_torus_add(major_radius=0.075, minor_radius=0.006, major_segments=32, minor_segments=8,
                                     location=(0, 0, 0.19), rotation=(math.radians(90), 0, 0))
    handle = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.object.mode_set(mode="OBJECT")
    bm = bmesh.new()
    bm.from_mesh(handle.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.002], context="VERTS")   # keep the upper arch
    bm.to_mesh(handle.data)
    bm.free()
    for o, m in ((body, skin), (flap, skin), (clasp, gilt), (handle, skin)):
        o.data.materials.append(m)
    ob = finish([body, flap, clasp, handle], "Borsetta")
    cube_uv(ob, 0.2)
    return export(ob, "Borsetta", {"made": "handbag", "grip_m": [0, 0, round(0.19 + 0.075, 3)]})


def occhiali():
    """Prescription glasses with a thick dark tortoiseshell frame (14 cm wide), clear lenses, folded-out arms."""
    reset()
    rng = np.random.default_rng(5)
    shell = noise(256, 256, 12, rng)
    tort = np.stack([0.10 + 0.25 * shell, 0.05 + 0.12 * shell, 0.02 + 0.03 * shell], -1)
    frame = material("M80_Occhiali_Tartaruga", image("occhiali_tartaruga", tort), rough=0.25)
    glass = material("M80_Occhiali_Lente", color=(0.85, 0.9, 0.9), rough=0.05, alpha=0.2)
    parts = []
    for side in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.025, minor_radius=0.0028, major_segments=32, minor_segments=8,
                                         location=(side * 0.033, 0, 0), rotation=(math.radians(90), 0, 0))
        ring = bpy.context.active_object
        ring.scale = (1.12, 0.85, 1.0)
        ring.data.materials.append(frame)
        bpy.ops.mesh.primitive_circle_add(vertices=32, radius=0.025, fill_type="NGON", location=(side * 0.033, 0, 0),
                                          rotation=(math.radians(90), 0, 0))
        lens = bpy.context.active_object
        lens.scale = (1.12, 0.85, 1.0)
        lens.data.materials.append(glass)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(side * 0.066, 0.065, 0.008))
        arm = bpy.context.active_object
        arm.scale = (0.003, 0.13, 0.005)
        arm.data.materials.append(frame)
        parts += [ring, lens, arm]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.012))
    bridge = bpy.context.active_object
    bridge.scale = (0.02, 0.004, 0.004)
    bridge.data.materials.append(frame)
    ob = finish(parts + [bridge], "OcchialiVista")
    cube_uv(ob, 0.05)
    return export(ob, "OcchialiVista", {"made": "glasses"})


def valigetta():
    """A brown leather briefcase (44 x 11 x 32 cm): rounded body, arched handle, two brass locks."""
    reset()
    rng = np.random.default_rng(7)
    skin = material("M80_Valigetta_Pelle", image("valigetta_pelle", leather(512, (0.20, 0.10, 0.045), rng)), rough=0.5)
    brass = material("M80_Valigetta_Ottone", color=(0.78, 0.62, 0.32), rough=0.3, metal=1.0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.16))
    body = bpy.context.active_object
    body.scale = (0.44, 0.11, 0.32)
    bpy.ops.object.transform_apply(scale=True)
    bev = body.modifiers.new("b", "BEVEL")
    bev.width, bev.segments = 0.015, 3
    bpy.ops.object.modifier_apply(modifier="b")
    body.data.materials.append(skin)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.05, minor_radius=0.009, major_segments=24, minor_segments=8,
                                     location=(0, 0, 0.32), rotation=(math.radians(90), 0, 0))
    handle = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(handle.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.002], context="VERTS")
    bm.to_mesh(handle.data)
    bm.free()
    handle.scale = (1.3, 1.0, 0.7)
    handle.data.materials.append(skin)
    parts = [body, handle]
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(side * 0.13, -0.057, 0.29))
        lock = bpy.context.active_object
        lock.scale = (0.035, 0.006, 0.022)
        lock.data.materials.append(brass)
        parts.append(lock)
    ob = finish(parts, "Valigetta")
    cube_uv(ob, 0.3)
    return export(ob, "Valigetta", {"made": "briefcase", "grip_m": [0, 0, round(0.32 + 0.05 * 0.7, 3)]})


def giornale():
    """A newspaper folded in four (30 x 21 cm), front page up, slightly bent."""
    reset()
    rng = np.random.default_rng(9)
    front = material("M80_Giornale_Prima", image("giornale_prima", newsprint(512, 720, rng)), rough=0.9)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=8, y_subdivisions=8, size=1)
    sheet = bpy.context.active_object
    sheet.scale = (0.21, 0.30, 1)
    bpy.ops.object.transform_apply(scale=True)
    for v in sheet.data.vertices:
        v.co.z = 0.004 + 0.01 * (v.co.x / 0.105) ** 2   # a soft bend across
    solid = sheet.modifiers.new("s", "SOLIDIFY")
    solid.thickness = 0.008
    bpy.ops.object.modifier_apply(modifier="s")
    sheet.data.materials.append(front)
    # Top view UVs: the page fills the 0-1 square.
    uv = sheet.data.uv_layers.active.data
    for poly in sheet.data.polygons:
        for li in poly.loop_indices:
            co = sheet.data.vertices[sheet.data.loops[li].vertex_index].co
            uv[li].uv = (co.x / 0.21 + 0.5, co.y / 0.30 + 0.5)
    ob = finish([sheet], "Giornale")
    return export(ob, "Giornale", {"made": "newspaper"})


def main():
    rng = np.random.default_rng(11)
    made = {
        "CoppolaQuadri": lambda: coppola("CoppolaQuadri", lambda: material("M80_Coppola_Quadri", image(
            "coppola_quadri", tartan(512, (0.78, 0.68, 0.5), [(0.0, 0.03, (0.1, 0.08, 0.06), 0.9), (0.25, 0.015, (0.6, 0.1, 0.08), 0.8),
                                                             (0.5, 0.03, (0.1, 0.08, 0.06), 0.9), (0.75, 0.01, (0.95, 0.93, 0.85), 0.7)], rng)),
            rough=0.9)),
        "CoppolaTweed": lambda: coppola("CoppolaTweed", lambda: material("M80_Coppola_Tweed", image(
            "coppola_tweed", tweed(512, [(0.32, 0.22, 0.13), (0.55, 0.42, 0.25), (0.12, 0.09, 0.07), (0.5, 0.3, 0.2)], rng)), rough=0.95)),
        "CoppolaGrigia": lambda: coppola("CoppolaGrigia", lambda: material("M80_Coppola_Grigia", image(
            "coppola_grigia", tweed(512, [(0.28, 0.28, 0.29), (0.4, 0.4, 0.42), (0.15, 0.15, 0.16)], rng)), rough=0.95)),
        "Borsetta": borsetta,
        "OcchialiVista": occhiali,
        "Valigetta": valigetta,
        "Giornale": giornale,
    }
    report = {}
    for key, cfg in DOWNLOADED.items():
        if not ONLY or key in ONLY:
            report[key] = downloaded(key, cfg)
    for key, fn in made.items():
        if not ONLY or key in ONLY:
            report[key] = fn()
    with open(os.path.join(OUT, "oggetti.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)


# Also imported by m80_bici.py for its helpers.
if __name__ == "__main__":
    main()
