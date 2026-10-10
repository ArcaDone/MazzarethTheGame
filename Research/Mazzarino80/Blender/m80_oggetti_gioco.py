"""The older hand-made models of the Unity project (D:/BitBucket/mazzareththegame/Assets: the bank, the hospital, Heaven)
made ready for Unreal: opened from where they were made, so their textures resolve; vegetation, scatter, references,
lights and vehicles left out (vegetation and vehicles are Unreal's); brought to real metres; the heaviest objects
decimated to a cap of triangles each; textures cut to MAX_PX and packed into the FBX, so Unreal builds their materials (base colour, normal) on import.
Run: blender -b --factory-startup --python m80_oggetti_gioco.py -- <Key> [preview]
Out: Saved/Mazzarino80/Oggetti/<Key>/{SM_M80_<Key>.fbx, <Key>.json, anteprima_*.png}
"""
import json
import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Matrix, Vector

UNITY = "D:/BitBucket/mazzareththegame/Assets"
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SAVED = os.path.join(ROOT, "Saved", "Mazzarino80", "Oggetti")
MAX_PX = 1024
SKIP_WORDS = ("gscatter", "bentgrass", "plantain", "moss", "grass", "vegetation", "albero", "ref", "light",
              "camera", "lights", "palm", "ambulance")

OGGETTI = {
    # scale: to real metres, from the human-sized parts. The bank was built about 2.5 times too big (doors 11.7 m,
    # windows 5.2 m), Heaven 5 times too small (birches 1.8 m, street lamps 0.8 m, benches 0.27 m); the hospital's
    # main block is 96 m long against the 86 m of its OSM footprint.
    # cap: triangles per object at most; budget: the whole model's, reached by collapsing the pieces over 500 alike.
    "Banca": {"blend": UNITY + "/Models2/banca.blend", "cap": 40000, "budget": 300000, "scale": 0.4},
    "Ospedale": {"blend": UNITY + "/Models2/ospedale.blend", "cap": 40000, "budget": 250000, "scale": 0.9},
    "Heaven": {"blend": UNITY + "/Models/Heaven/Heaven.blend", "cap": 40000, "budget": 250000, "scale": 5.0},
}


def skipped(o):
    names = " ".join([o.name] + [c.name for c in o.users_collection]).lower()
    return any(w in names for w in SKIP_WORDS)


def evaluated_copy(o, scale):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    if not me.polygons:
        bpy.data.meshes.remove(me)
        return None
    me.transform(Matrix.Scale(scale, 4) @ o.matrix_world)
    if o.matrix_world.determinant() < 0:
        me.flip_normals()
    cp = bpy.data.objects.new(o.name + "_g", me)
    bpy.context.scene.collection.objects.link(cp)
    return cp


def reduce(o, cap):
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if tris <= cap:
        return tris
    bpy.context.view_layer.objects.active = o
    # First the flat parts (coplanar faces merged), then a collapse down to the cap.
    m = o.modifiers.new("planar", "DECIMATE")
    m.decimate_type = "DISSOLVE"
    m.angle_limit = math.radians(1.0)
    bpy.ops.object.modifier_apply(modifier=m.name)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(o.data)
    bm.free()
    t2 = len(o.data.polygons)
    if t2 > cap:
        m = o.modifiers.new("collapse", "DECIMATE")
        m.ratio = cap / float(t2)
        bpy.ops.object.modifier_apply(modifier=m.name)
    out = len(o.data.polygons)
    print("reduce %s: %d -> %d" % (o.name, tris, out))
    return out


def shrink(folder):
    for name in [os.path.relpath(os.path.join(d, f), folder) for d, _, fs in os.walk(folder) for f in fs]:
        p = os.path.join(folder, name)
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".bmp")) or os.path.basename(name).startswith("anteprima"):
            continue
        img = bpy.data.images.load(p, check_existing=False)
        w, h = img.size
        if max(w, h) > MAX_PX:
            s = MAX_PX / float(max(w, h))
            img.scale(max(1, int(w * s)), max(1, int(h * s)))
            img.filepath_raw = p
            img.save()
        bpy.data.images.remove(img)


def build(key, preview):
    t0 = time.time()
    cfg = OGGETTI[key]
    out_dir = os.path.join(SAVED, key)
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=cfg["blend"])
    src = [o for o in bpy.context.scene.objects if o.type in ("MESH", "CURVE", "FONT") and not o.hide_render and not skipped(o)]
    copies = [c for c in (evaluated_copy(o, cfg.get("scale", 1.0)) for o in src) if c]
    for o in list(bpy.context.scene.objects):
        if o not in copies:
            o.hide_render = True
    tris = {c.name: reduce(c, cfg["cap"]) for c in copies}
    heavy = sum(t for t in tris.values() if t > 500)
    light = sum(tris.values()) - heavy
    if heavy + light > cfg["budget"]:
        ratio = max(0.05, (cfg["budget"] - light) / float(heavy))
        for c in copies:
            if tris[c.name] > 500:
                tris[c.name] = reduce(c, int(tris[c.name] * ratio))
    missing = sorted({i.name for i in bpy.data.images if i.source == "FILE" and not os.path.exists(bpy.path.abspath(i.filepath))})
    bpy.ops.object.select_all(action="DESELECT")
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = "SM_M80_" + key
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    lo = Vector([min((ob.matrix_world @ v.co)[i] for v in ob.data.vertices) for i in range(3)])
    hi = Vector([max((ob.matrix_world @ v.co)[i] for v in ob.data.vertices) for i in range(3)])
    fbx = "SM_M80_%s.fbx" % key
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(out_dir, fbx), use_selection=True, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z", object_types={"MESH"},
                             mesh_smooth_type="FACE", bake_space_transform=True, path_mode="COPY", embed_textures=False)
    # The textures the FBX copied next to itself, cut to MAX_PX (Unreal reads them from there on import).
    shrink(out_dir)
    manifest = {"key": key, "source": cfg["blend"], "fbx": fbx, "triangles": len(ob.data.polygons),
                "pieces": tris, "bounds_m": [list(lo), list(hi)], "missing_textures": missing,
                "materials": sorted({m.name for m in ob.data.materials if m}), "scale": cfg.get("scale", 1.0)}
    json.dump(manifest, open(os.path.join(out_dir, key + ".json"), "w", encoding="utf-8"), indent=1)
    print("M80 oggetto %s: %d triangles, %d missing textures, %.0f s" % (key, manifest["triangles"], len(missing), time.time() - t0))
    if preview:
        sc = bpy.context.scene
        sc.render.engine = "BLENDER_EEVEE"
        sc.render.resolution_x, sc.render.resolution_y = 1280, 800
        cam = bpy.data.objects.new("CamP", bpy.data.cameras.new("CamP"))
        cam.data.clip_end = 10000
        sc.collection.objects.link(cam)
        sc.camera = cam
        sun = bpy.data.objects.new("SunP", bpy.data.lights.new("SunP", "SUN"))
        sun.data.energy = 4
        sun.rotation_euler = (math.radians(45), 0, math.radians(30))
        sc.collection.objects.link(sun)
        c = (lo + hi) / 2
        L = max(hi.x - lo.x, hi.y - lo.y)
        for k, ang in enumerate((30, 150, 270)):
            a = math.radians(ang)
            eye = c + Vector((math.cos(a) * L * 0.9, math.sin(a) * L * 0.9, L * 0.5))
            cam.location = eye
            cam.rotation_euler = (c - eye).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = os.path.join(out_dir, "anteprima_%d.png" % k)
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for k in args:
        if k in OGGETTI:
            build(k, "preview" in args)
