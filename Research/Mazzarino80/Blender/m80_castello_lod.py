"""Blender 5.2: hand-made LODs for the castle's meshes, the pieces of the Blueprint CastelCompleted in the town.

With Nanite the castle turns black from far away: Nanite goes off and every piece gets its own LODs instead.
Run: blender -b --python m80_castello_lod.py -- <src_dir> <out_dir> [foto_dir]
- src_dir: the meshes exported from Unreal as they are drawn (Scripts/m80_castello_esporta.py), so every LOD sits
  exactly on its LOD0 and keeps its material slots;
- each piece gets the LODs listed in PIECES, each a mix of three steps: drop the loose parts smaller than "drop" m
  (single stones, planks, the wire net: too small to see from that far), dissolve faces flatter than "planar" degrees
  into one (walls keep their outline, texturing kept: material and UV borders stay), collapse edges to "ratio" of the
  triangles (only on the ruin and the rocks, which stay one rough surface); custom normals cleared and smoothed by
  angle; pieces not listed (the base and the low walls, a few hundred triangles) stay as they are;
- saves D:/Mazzarino80_Sorgenti/Edifici/Castello/CastelloLOD.blend (one collection per LOD, LOD1+ hidden, to retouch
  by hand; refuses to overwrite it without M80_SOVRASCRIVI=1) and exports out_dir/<piece>_LOD<n>.fbx;
  with M80_DAL_BLEND=1 the LODs are exported from that file as it is (after a retouch) instead of being rebuilt;
- foto_dir: every piece's LODs side by side (lod.json lists the triangles).
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SRC, OUT = os.path.abspath(ARGS[0]), os.path.abspath(ARGS[1])
FOTO = os.path.abspath(ARGS[2]) if len(ARGS) > 2 else ""
BLEND = r"D:/Mazzarino80_Sorgenti/Edifici/Castello/CastelloLOD.blend"
# piece -> its LOD1, LOD2... (drop: loose parts under this size in m; planar: degrees; ratio: of the triangles left)
PIECES = {
    "MainCastello_001": [{"planar": 2, "ratio": 0.5}, {"planar": 5, "ratio": 0.25}, {"planar": 8, "ratio": 0.13}],
    "Rocks": [{"ratio": 0.5}, {"ratio": 0.2}],
    "Anfiteatro": [{"drop": 1.0, "planar": 10}, {"drop": 2.0, "planar": 25}],
    "Staccionata": [{"drop": 1.5, "planar": 15}, {"drop": 2.0, "planar": 15}],
    # the gate keeps its LOD0: 2300 triangles, and without its bars it would look open
    # the spiral stair stays, its wire net (five sheets of 0.24 m diamonds, 2500 faces each) goes from the first LOD
    "Rete": [{"net": 0.3, "planar": 5}],
}
MIN_TRIS = 150
NET_FACES = 1000
SHARP_DEG = 40.0


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def collection(name, hidden=False):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    c.hide_render = hidden
    lc = bpy.context.view_layer.layer_collection.children.get(name)
    if lc:
        lc.hide_viewport = hidden
    return c


def smooth_by_angle(o):
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
        if o.data.has_custom_normals:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    o.data.set_sharp_from_angle(angle=math.radians(SHARP_DEG))


def drop_small(bm, size, net=0.0):
    """Deletes the loose parts whose box is smaller than size (m, world), and with net the wire nets: parts of more
    than NET_FACES faces whose edges are shorter than net (m) on average, whatever their size."""
    bm.verts.ensure_lookup_table()
    seen, doomed = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        part, stack = [], [v]
        seen.add(v)
        while stack:
            x = stack.pop()
            part.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        lo = Vector((min(p.co.x for p in part), min(p.co.y for p in part), min(p.co.z for p in part)))
        hi = Vector((max(p.co.x for p in part), max(p.co.y for p in part), max(p.co.z for p in part)))
        edges = {e for x in part for e in x.link_edges}
        faces = {f for x in part for f in x.link_faces}
        wire = net and len(faces) > NET_FACES and sum(e.calc_length() for e in edges) / len(edges) < net
        if (hi - lo).length < size or wire:
            doomed.extend(part)
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")


def make_lod(src, n, cfg):
    o = src.copy()
    o.data = src.data.copy()
    o.name = "%s_LOD%d" % (src.name.rsplit("_LOD", 1)[0], n)
    collection("LOD%d" % n, hidden=n > 0).objects.link(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    if cfg.get("drop") or cfg.get("net"):
        # sizes in world metres: the mesh carries the FBX's 0.01 object scale
        bm.transform(o.matrix_world)
        drop_small(bm, cfg.get("drop", 0.0), cfg.get("net", 0.0))
        bm.transform(o.matrix_world.inverted())
    if cfg.get("planar"):
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(cfg["planar"]), use_dissolve_boundaries=False,
                                 verts=bm.verts[:], edges=bm.edges[:], delimit={"MATERIAL", "UV", "SEAM"})
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(o.data)
    bm.free()
    if cfg.get("ratio"):
        target = max(MIN_TRIS, int(tris(src) * cfg["ratio"]))
        mod = o.modifiers.new("Decimate", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = min(1.0, target / max(1, tris(o)))
        mod.use_collapse_triangulate = True
        with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    smooth_by_angle(o)
    return o


def build():
    bpy.ops.wm.read_homefile(use_empty=True)
    for f in sorted(os.listdir(SRC)):
        if not f.lower().endswith(".fbx"):
            continue
        name = f[:-4]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(SRC, f))
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        if not new:
            print("M80 niente in", f)
            continue
        o = new[0]
        o.name = name + "_LOD0"
        for c in list(o.users_collection):
            c.objects.unlink(o)
        collection("LOD0").objects.link(o)
        for extra in [x for x in bpy.data.objects if x not in before and x is not o]:
            bpy.data.objects.remove(extra)
        for n, cfg in enumerate(PIECES.get(name, []), start=1):
            make_lod(o, n, cfg)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


def export():
    os.makedirs(OUT, exist_ok=True)
    # hidden collections export nothing: everything shown (the file is not saved after this)
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.hide_viewport = False
        lc.exclude = False
    rep = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or "_LOD" not in o.name:
            continue
        piece, lod = o.name.rsplit("_LOD", 1)
        rep.setdefault(piece, {})["LOD" + lod] = tris(o)
        bpy.ops.object.select_all(action="DESELECT")
        o.hide_set(False)
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        # the object is exported with its own transform: Unreal bakes it, as it did for the source
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, o.name + ".fbx"), use_selection=True, object_types={"MESH"},
                                 mesh_smooth_type="FACE", use_visible=False, path_mode="STRIP", bake_anim=False)
    with open(os.path.join(OUT, "lod.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    for piece, lods in sorted(rep.items()):
        print("M80", piece, lods)
    return rep


def views(rep):
    sc = bpy.context.scene
    os.makedirs(FOTO, exist_ok=True)
    cam = bpy.data.objects.new("C", bpy.data.cameras.new("C"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "SINGLE"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 1800, 600
    for c in sc.collection.children:
        c.hide_render = False
    for piece, lods in rep.items():
        objs = [bpy.data.objects[piece + "_" + k] for k in sorted(lods)]
        for o in bpy.data.objects:
            o.hide_render = o.type == "MESH" and o not in objs
        lo = [o.matrix_world @ Vector(v) for v in objs[0].bound_box]
        size = Vector((max(v.x for v in lo) - min(v.x for v in lo), max(v.y for v in lo) - min(v.y for v in lo),
                       max(v.z for v in lo) - min(v.z for v in lo)))
        step = max(size.x, size.y) * 1.15
        base = [o.location.copy() for o in objs]
        for i, o in enumerate(objs):
            o.location.x = base[i].x + i * step
        ctr = sum((o.matrix_world @ Vector(v) for v in objs[0].bound_box), Vector()) / 8
        ctr.x += step * (len(objs) - 1) / 2
        width = step * len(objs)
        cam.location = Vector((ctr.x, ctr.y - width * 1.3, ctr.z + width * 0.35))
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 50
        sc.render.filepath = os.path.join(FOTO, "lod_%s.png" % piece)
        bpy.ops.render.render(write_still=True)
        for i, o in enumerate(objs):
            o.location = base[i]


def main():
    if os.environ.get("M80_DAL_BLEND") == "1":
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    elif os.path.exists(BLEND) and os.environ.get("M80_SOVRASCRIVI") != "1":
        print("M80 CastelloLOD.blend esiste gia': M80_SOVRASCRIVI=1 per rifarlo, M80_DAL_BLEND=1 per esportarlo")
        return
    else:
        build()
    rep = export()
    if FOTO:
        views(rep)


main()
