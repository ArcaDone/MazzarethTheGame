"""Blender 4.3: quick preview of a .blend (Workbench, material colours) + world bounding box and
material node summary -> <out>.png and <out>_info.json.

Run: blender -b <file.blend> --python m80_preview_blend.py -- <out_prefix>
"""
import json
import math
import sys

import bpy
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1]
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH" and not o.hide_render and o.visible_get()]
lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w))
        hi = Vector(map(max, hi, w))
size = hi - lo
centre = (lo + hi) / 2
info = {"bbox_min": list(lo), "bbox_max": list(hi), "size": list(size), "objects": len(meshes)}
nodes = {}
for m in bpy.data.materials:
    if m.users and m.use_nodes and m.node_tree:
        kinds = sorted({n.type for n in m.node_tree.nodes})
        nodes[m.name] = kinds
info["material_nodes"] = nodes
with open(OUT + "_info.json", "w", encoding="utf-8") as f:
    json.dump(info, f, indent=1)

# Camera at 3/4 front, looking at the centre, far enough for the whole model.
cam_data = bpy.data.cameras.new("M80Cam")
cam = bpy.data.objects.new("M80Cam", cam_data)
scene.collection.objects.link(cam)
r = max(size) * 1.4
cam.location = centre + Vector((r * 0.8, -r * 0.9, r * 0.55))
d = centre - cam.location
cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
cam_data.lens = 40
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.render.resolution_x = 1200
scene.render.resolution_y = 800
scene.render.film_transparent = False
scene.render.filepath = OUT + ".png"
bpy.ops.render.render(write_still=True)
print("M80 preview", OUT, [round(v, 2) for v in size])
