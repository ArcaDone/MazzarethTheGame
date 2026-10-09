"""Palazzo Bartoli for the game: high-poly block -> retopology (the *_Low collections), UV, bake, FBX for Unreal.

Builds the block as the "alta" stage does (m80_palazzo_bartoli.py), without the interiors for now (M80_INTERNI=0: the
openings keep their dark plates), then for every group with a high and a low collection (facades, staircase and
loggia, carriage passage, courtyard, gardens):
  - joins the low-poly parts, welds them, unwraps one atlas (smart project, uniform texel density);
  - bakes from the high-poly: colour, tangent normal, AO + roughness (ORM), size from the surface (M80_BAKE_PX_M px/m,
    512-4096) -> Textures/Bartoli/T_Bartoli_<group>_{D,N,ORM};
  - joins its fittings (shutters, glass, doors, iron, signs, eave tiles; curves and text made mesh) into one mesh with
    one slot per material, box UVs in metres, for the town materials in Unreal.
Roofs: plain planes with UVs in metres (Unreal's tiling coppi) and the ridge rows as mesh; the dark volumes behind the
facades, parapets and the ruin: one mesh with box UVs. Greenery markers go to the manifest.
Everything keeps the lot's local metres: pivot at origin_world_cm of Lots/1249067196_layout.json, so in Unreal all the
pieces sit at the same location (X forward, Y mirrored as usual for Blender -> Unreal).

Run: blender -b --factory-startup --python m80_bartoli_bake.py -- bake
     (-- footprint: only adds the block's plan raster to the manifest of the last bake, from bartoli_bake.blend)
Env: M80_BAKE_ONLY=C_Corso,Scalone (only those groups, for tests), M80_BAKE_PX_M (default 128), M80_SAMPLES (48, occlusion pass),
M80_BAKE_DIR=<folder> (export, textures and .blend there instead of the usual places: tests that leave the block's bake
alone), M80_BAKE_MERGE=0 (bake from the separate high-poly pieces, see m80_palazzo_bartoli.merged_high).
Out: Saved/Mazzarino80/Bartoli/Export/M80_Bartoli.fbx + M80_Bartoli.json, bartoli_bake.blend.
"""
import json
import math
import os
import sys
import time
import types

import bmesh
import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HERE)
os.environ.setdefault("M80_INTERNI", "0")
import m80_arch_kit as K  # noqa: E402
import m80_palazzo_bartoli as P  # noqa: E402  (stage "bake" is not one of its own: importing it runs nothing)

P.K = K
P.time = time
OUT_DIR = os.environ.get("M80_BAKE_DIR")
EXPORT = OUT_DIR or os.path.join(P.SAVED, "Export")
if OUT_DIR:
    P.TEXTURES = os.path.join(OUT_DIR, "Textures")
DENSITY = float(os.environ.get("M80_BAKE_PX_M", "128"))
ONLY = [g for g in os.environ.get("M80_BAKE_ONLY", "").split(",") if g]
PREFIX = "SM_M80_Bartoli_"
MANIFEST = "M80_Bartoli.json" if not ONLY else "M80_Bartoli_prova.json"
# Scene-root parts that go to the game as plain volumes (everything else at the root is terrain or neighbours).
MASS_PREFIXES = ("Massa_", "Crema_parapetto", "B_muri_pensile", "Rudere_macerie", "Muro_cinta")


def groups():
    names = []
    for c in bpy.data.collections:
        if c.name.endswith("_High") and c.name != "Tetti_High":
            base = c.name[:-5]
            if bpy.data.collections.get(base + "_Low") and any(o.type == "MESH" for o in bpy.data.collections[base + "_Low"].objects):
                names.append(base)
    return [n for n in sorted(names) if not ONLY or n in ONLY]


def group(name):
    det = bpy.data.collections.get(name + "_Detail") or K.collection(name + "_Detail")
    return types.SimpleNamespace(name=name, high=bpy.data.collections[name + "_High"], low=bpy.data.collections[name + "_Low"], detail=det)


def flatten(ob):
    """World transform into the mesh, no parent: every exported piece has its pivot at the lot origin."""
    mw = ob.matrix_world.copy()
    ob.parent = None
    ob.data.transform(mw)
    ob.matrix_world = Matrix.Identity(4)
    if mw.determinant() < 0:
        ob.data.flip_normals()
    return ob


def select_only(objs, active):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


def join(objs, name):
    select_only(objs, objs[0])
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = name
    return flatten(ob)


def area(ob):
    return sum(p.area for p in ob.data.polygons)


def bake_size(ob):
    side = math.sqrt(max(area(ob), 1.0) * 1.3) * DENSITY
    return int(min(4096, max(512, 2 ** round(math.log2(side)))))


def retopo_low(G):
    """Low parts of a group -> one clean mesh with its own material and one UV atlas."""
    objs = [o for o in G.low.objects if o.type == "MESH"]
    low = join(objs, PREFIX + G.name)
    me = low.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UVMap")
    mat = bpy.data.materials.new("Bake_" + G.name)
    mat.use_nodes = True
    me.materials.clear()
    me.materials.append(mat)
    for p in me.polygons:
        p.material_index = 0
    size = bake_size(low)
    select_only([low], low)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    margin = 6.0 / size
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=margin, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=margin, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    # Smooth across slightly bent faces: the garden wall along the street follows the ground with a fan of triangles,
    # flat shaded it came out in Unreal as a fan of light and dark facets. Real corners (over 35 degrees) stay sharp;
    # the bake's tangent space and Unreal's both use these normals.
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    return low, size


def box_uv(ob, size=1.0):
    """UVs in metres projected on the dominant axis of each face (like the house builder's walls: V down)."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for loop in f.loops:
            c = loop.vert.co
            if ax == 2:
                loop[uv].uv = (c.x / size, c.y / size)
            elif ax == 0:
                loop[uv].uv = (c.y / size, -c.z / size)
            else:
                loop[uv].uv = (c.x / size, -c.z / size)
    bm.to_mesh(me)
    bm.free()


def as_meshes(objs, name):
    """Meshes, curves and text (modifiers applied) as one mesh object keeping the material slots."""
    dg = bpy.context.evaluated_depsgraph_get()
    parts = []
    for o in objs:
        if o.type not in ("MESH", "CURVE", "FONT") or o.hide_render:
            continue
        ev = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=False, depsgraph=dg)
        if not me.polygons:
            bpy.data.meshes.remove(me)
            continue
        me.transform(o.matrix_world)
        if o.matrix_world.determinant() < 0:
            me.flip_normals()
        ob = bpy.data.objects.new(o.name + "_m", me)
        bpy.context.scene.collection.objects.link(ob)
        parts.append(ob)
    if not parts:
        return None
    ob = join(parts, name)
    me = ob.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UVMap")
    box_uv(ob)
    return ob


def slots(ob):
    return [m.name if m else "" for m in ob.data.materials]


def material_info(names):
    """Base colour (linear), metallic, roughness and emission of the fittings' materials, for Unreal instances."""
    out = {}
    for n in names:
        m = bpy.data.materials.get(n)
        if not m:
            continue
        rec = {"color": [round(v, 4) for v in m.diffuse_color[:3]], "metal": 0.0, "rough": 0.8, "emission": 0.0}
        b = m.node_tree.nodes.get("Principled BSDF") if m.use_nodes else None
        if b:
            rec["color"] = [round(v, 4) for v in b.inputs["Base Color"].default_value[:3]]
            rec["metal"] = round(b.inputs["Metallic"].default_value, 3)
            rec["rough"] = round(b.inputs["Roughness"].default_value, 3)
            rec["emission"] = round(b.inputs["Emission Strength"].default_value, 3)
        out[n] = rec
    return out


def markers():
    out = []
    col = bpy.data.collections.get("Vegetazione_Marker")
    for o in (col.all_objects if col else []):
        p = o.matrix_world.translation
        rec = {"name": o.name, "local_m": [round(p.x, 3), round(p.y, 3), round(p.z, 3)]}
        for k in o.keys():
            v = o[k]
            rec[k] = list(v) if hasattr(v, "__len__") and not isinstance(v, str) else v
        out.append(rec)
    return out


def only_high(name):
    for lc in bpy.context.view_layer.layer_collection.children:
        if lc.name.endswith("_High"):
            lc.exclude = name is not None and lc.name != name + "_High"


def block():
    """Outlines of the block in world cm (lot, cinema, cream house): the procedural houses standing there give way."""
    ox, oy, _ = P.LAYOUT["origin_world_cm"]
    polys = [[[round(p[0], 1), round(p[1], 1)] for p in P.TERRAIN["footprint"]]]
    for poly in (P.CINEMA, P.CREMA):
        polys.append([[round(ox + x * 100.0, 1), round(oy - y * 100.0, 1)] for x, y in poly])
    return polys


def main():
    t0 = time.time()
    P.reset()
    print("GPU:", P.use_gpu())
    P.build_all(float(os.environ.get("M80_WALL_STEP", "0.03")))
    print("built %.0f s" % (time.time() - t0))
    sc = bpy.context.scene
    os.makedirs(EXPORT, exist_ok=True)
    manifest = {"units": "cm", "origin_world_cm": P.LAYOUT["origin_world_cm"],
                "note": "every mesh has its pivot at origin_world_cm: place them all there with no rotation",
                "groups": {}, "details": {}, "markers": markers(), "block_world_cm": block()}
    exported = []
    for name in groups():
        G = group(name)
        t = time.time()
        low, size = retopo_low(G)
        # Only this group's high-poly in the scene while baking: every bake pass re-syncs the scene, and with all
        # the block's displaced stone that takes minutes. The other groups' low-poly stays for the occlusion.
        only_high(name)
        files = P.bake_low(G, low, size)
        only_high(None)
        tris = sum(len(p.vertices) - 2 for p in low.data.polygons)
        manifest["groups"][name] = {"mesh": low.name, "size": size, "area_m2": round(area(low), 1), "triangles": tris,
                                    "textures": {k: os.path.basename(v) for k, v in files.items()}}
        exported.append(low)
        det = as_meshes(list(G.detail.all_objects), PREFIX + name + "_Dettagli")
        if det:
            manifest["details"][name] = {"mesh": det.name, "slots": slots(det), "triangles": sum(len(p.vertices) - 2 for p in det.data.polygons)}
            exported.append(det)
        print("group %s %dpx %.0f s" % (name, size, time.time() - t))
        with open(os.path.join(EXPORT, MANIFEST), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=1)
    if not ONLY:
        roofs = [o for o in bpy.data.collections["Tetti_Low"].objects if o.type == "MESH"]
        roof = join(roofs, PREFIX + "Tetti")
        roof.data.materials.clear()
        roof.data.materials.append(bpy.data.materials.get("Coppi") or bpy.data.materials.new("Coppi"))
        for p in roof.data.polygons:
            p.material_index = 0
        exported.append(roof)
        ridges = as_meshes([o for o in bpy.data.collections["Tetti_High"].objects if o.type == "CURVE"], PREFIX + "Tetti_Colmi")
        if ridges:
            exported.append(ridges)
        mass = as_meshes([o for o in sc.collection.objects if o.name.startswith(MASS_PREFIXES)], PREFIX + "Volumi")
        exported.append(mass)
        manifest["roofs"] = {"mesh": roof.name, "ridges": ridges.name if ridges else None, "uv": "metres, u along the eave, v up the slope"}
        manifest["volumes"] = {"mesh": mass.name, "slots": slots(mass)}
    select_only(exported, exported[0])
    fbx = os.path.join(EXPORT, "M80_Bartoli.fbx" if not ONLY else "M80_Bartoli_prova.fbx")
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True)
    used = sorted({n for d in manifest["details"].values() for n in d["slots"]} | set(manifest.get("volumes", {}).get("slots", [])))
    manifest["materials"] = material_info(used)
    manifest["footprint"] = footprint(plan_objects())
    manifest["fbx"] = os.path.basename(fbx)
    manifest["seconds"] = round(time.time() - t0)
    with open(os.path.join(EXPORT, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR or P.SAVED, "bartoli_bake.blend"))
    print("M80 Bartoli exported %s in %.0f s" % (fbx, time.time() - t0))


def footprint(objs, cell=0.5):
    """Where the block stands, as a raster of cell x cell metres (lot local x, y): the plan projection of the roofs,
    floors, gardens and volumes (walls project to lines and add nothing), one cell of margin. Unreal hides the town's
    procedural houses standing on it (m80_bartoli_town_views.py). Rows south to north, '1' = block."""
    import numpy as np
    tris = []
    for ob in objs:
        me = ob.data
        me.calc_loop_triangles()
        co = np.array([(ob.matrix_world @ v.co)[:2] for v in me.vertices])
        idx = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int64).reshape(-1, 3)
        if len(idx):
            tris.append(co[idx])
    tris = np.concatenate(tris)
    x0, y0 = np.floor(tris.reshape(-1, 2).min(0) / cell) * cell - cell
    x1, y1 = np.ceil(tris.reshape(-1, 2).max(0) / cell) * cell + cell
    w, h = int(round((x1 - x0) / cell)), int(round((y1 - y0) / cell))
    grid = np.zeros((h, w), dtype=bool)
    for a, b, c in tris:
        d = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(d) < 1e-6:
            continue
        lo, hi = np.minimum(np.minimum(a, b), c), np.maximum(np.maximum(a, b), c)
        i0, i1 = int((lo[0] - x0) / cell), int((hi[0] - x0) / cell) + 1
        j0, j1 = int((lo[1] - y0) / cell), int((hi[1] - y0) / cell) + 1
        px, py = np.meshgrid(x0 + (np.arange(i0, i1) + 0.5) * cell, y0 + (np.arange(j0, j1) + 0.5) * cell)
        l1 = ((b[0] - px) * (c[1] - py) - (b[1] - py) * (c[0] - px)) / d
        l2 = ((c[0] - px) * (a[1] - py) - (c[1] - py) * (a[0] - px)) / d
        grid[j0:j1, i0:i1] |= (l1 >= -0.02) & (l2 >= -0.02) & (l1 + l2 <= 1.02)
    grown = grid.copy()
    grown[1:] |= grid[:-1]; grown[:-1] |= grid[1:]; grown[:, 1:] |= grid[:, :-1]; grown[:, :-1] |= grid[:, 1:]
    return {"cell": cell, "x0": round(float(x0), 2), "y0": round(float(y0), 2), "w": w, "h": h,
            "rows": ["".join("1" if v else "0" for v in row) for row in grown]}


def footprint_only():
    """Adds the footprint to the manifest of an existing bake (bartoli_bake.blend) without baking again."""
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT_DIR or P.SAVED, "bartoli_bake.blend"))
    path = os.path.join(EXPORT, MANIFEST)
    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)
    manifest["footprint"] = footprint(plan_objects())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print("M80 Bartoli footprint", manifest["footprint"]["w"], "x", manifest["footprint"]["h"])


def plan_objects():
    return [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(PREFIX) and not o.name.endswith("_Dettagli")
            and o.name != PREFIX + "Tetti_Colmi"]


if "footprint" in sys.argv:
    footprint_only()
else:
    main()
