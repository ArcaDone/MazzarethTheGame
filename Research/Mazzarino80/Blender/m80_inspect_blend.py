"""Blender 4.3: inventory of a .blend before importing it into Unreal -> JSON.

Run: blender -b <file.blend> --python m80_inspect_blend.py -- <out.json>
Per object: type, parent, visibility, vertices / triangles before and after modifiers, modifiers
(with subdivision levels), materials, size; per image: resolution, packed or file, users; totals.
"""
import json
import sys

import bpy

OUT = sys.argv[sys.argv.index("--") + 1]
dg = bpy.context.evaluated_depsgraph_get()
objs = []
tot_raw = tot_eval = 0
for o in bpy.data.objects:
    d = {"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
         "hidden": o.hide_get() if o.name in bpy.context.view_layer.objects else True, "hide_render": o.hide_render,
         "collections": [c.name for c in o.users_collection], "dims": [round(v, 3) for v in o.dimensions]}
    if o.type == "MESH":
        me = o.data
        raw = sum(len(p.vertices) - 2 for p in me.polygons)
        d["verts"] = len(me.vertices)
        d["tris"] = raw
        d["mods"] = []
        for m in o.modifiers:
            md = {"type": m.type, "name": m.name, "show_render": m.show_render}
            if m.type == "SUBSURF":
                md["levels"] = m.levels
                md["render_levels"] = m.render_levels
            if m.type == "DECIMATE":
                md["ratio"] = getattr(m, "ratio", None)
            if m.type in ("ARRAY", "MIRROR", "BEVEL", "SOLIDIFY", "BOOLEAN"):
                md["detail"] = {k: str(getattr(m, k)) for k in ("count", "segments", "thickness", "object") if hasattr(m, k)}
            d["mods"].append(md)
        try:
            ev = o.evaluated_get(dg)
            em = ev.to_mesh()
            d["tris_eval"] = sum(len(p.vertices) - 2 for p in em.polygons)
            ev.to_mesh_clear()
        except Exception as e:  # noqa: BLE001
            d["tris_eval"] = "error %s" % e
        d["materials"] = [s.material.name if s.material else None for s in o.material_slots]
        d["uv_layers"] = len(me.uv_layers)
        tot_raw += raw
        if isinstance(d["tris_eval"], int) and not d["hide_render"]:
            tot_eval += d["tris_eval"]
    elif o.type == "ARMATURE":
        d["bones"] = [b.name for b in o.data.bones]
    objs.append(d)
imgs = []
for im in bpy.data.images:
    imgs.append({"name": im.name, "size": list(im.size), "packed": im.packed_file is not None, "file": im.filepath,
                 "users": im.users, "colorspace": im.colorspace_settings.name})
mats = []
for m in bpy.data.materials:
    tex = []
    if m.use_nodes and m.node_tree:
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                tex.append(n.image.name)
    mats.append({"name": m.name, "users": m.users, "images": tex})
rep = {"file": bpy.data.filepath, "unit_scale": bpy.context.scene.unit_settings.scale_length, "objects": objs,
       "images": imgs, "materials": mats, "tris_raw": tot_raw, "tris_eval_render": tot_eval,
       "scenes": [s.name for s in bpy.data.scenes], "collections": [c.name for c in bpy.data.collections]}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rep, f, indent=1)
print("M80 inspected", OUT, tot_raw, tot_eval)
