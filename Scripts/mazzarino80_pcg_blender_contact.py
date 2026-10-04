"""Render a small, read-only contact set from CaseSoluzione.blend."""
import math
from pathlib import Path

import bpy
from mathutils import Vector


OUT = Path("D:/UE5Projects/GameAnimationSample/Saved/Mazzarino80/PCG/Golden")
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.render.film_transparent = True
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.camera = bpy.data.objects.get("Camera") or bpy.data.objects.new("PCG_Inspection_Camera", bpy.data.cameras.new("PCG_Inspection_Camera"))
camera = scene.camera
camera.data.type = "ORTHO"
names = ("Ground", "Ground.014", "RoofPopolari001", "RoofCornerPopolari001", "window.010", "window.011")

for obj in bpy.data.objects:
    if obj.type in {"MESH", "CURVE", "FONT"}:
        obj.hide_render = True

for name in names:
    obj = bpy.data.objects[name]
    obj.hide_render = False
    box = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector(tuple(min(vertex[i] for vertex in box) for i in range(3)))
    maximum = Vector(tuple(max(vertex[i] for vertex in box) for i in range(3)))
    center = (minimum + maximum) / 2
    size = max((maximum - minimum).length, 0.5)
    camera.location = center + Vector((size * 1.3, -size * 1.6, size * 1.1))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = size * 1.7
    scene.render.filepath = str(OUT / f"{name.replace('.', '_')}.png")
    bpy.ops.render.render(write_still=True)
    obj.hide_render = True
    print("M80_GOLDEN_RENDER", name, scene.render.filepath)
