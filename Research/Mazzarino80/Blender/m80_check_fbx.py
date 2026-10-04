"""Blender 4.3: render an exported FBX from the front-left 3/4 and from the side, with the bones, to check
scale, orientation (front +X), wheels on the ground. Run: blender -b --factory-startup --python m80_check_fbx.py -- <in.fbx> <out_prefix>"""
import math
import sys

import bpy
from mathutils import Vector

FBX, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH"]
lo = Vector((1e9, 1e9, 1e9))
hi = -lo
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w))
        hi = Vector(map(max, hi, w))
size = hi - lo
centre = (lo + hi) / 2
print("M80 size", [round(v, 3) for v in size], "min", [round(v, 3) for v in lo])
# Ground plane and a red marker in front (+X) so orientation is obvious.
bpy.ops.mesh.primitive_plane_add(size=max(size) * 3, location=(centre.x, centre.y, 0))
bpy.ops.mesh.primitive_cone_add(radius1=0.08, depth=0.3, location=(hi.x + 0.4, 0, 0.15), rotation=(0, math.pi / 2, 0))
mark = bpy.context.active_object
mat = bpy.data.materials.new("Red")
mat.diffuse_color = (1, 0, 0, 1)
mark.data.materials.append(mat)
cam_data = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_xray = False
scene.render.resolution_x = 1200
scene.render.resolution_y = 700
for o in scene.objects:
    if o.type == "ARMATURE":
        o.show_in_front = True
for name, offs in (("34", Vector((1.0, 1.0, 0.55))), ("lato", Vector((0.0, 1.0, 0.15)))):
    r = max(size) * 1.25
    cam.location = centre + offs.normalized() * r
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = OUT + "_" + name + ".png"
    bpy.ops.render.render(write_still=True)
