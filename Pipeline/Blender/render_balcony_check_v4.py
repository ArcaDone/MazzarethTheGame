"""Render street and plan checks of the complete STYLE_03 balcony module."""
from pathlib import Path
import bpy
from mathutils import Vector

out = Path(__file__).resolve().parent / "output/style03_reference_v4"
bpy.ops.wm.open_mainfile(filepath=str(out / "Mazzarino_STYLE_03_Reference_Gate_v4.blend"))
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 64
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"

def take(name, location, target, scale):
    camera_data = bpy.data.cameras.new(name)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = scale
    camera = bpy.data.objects.new(name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    scene.render.filepath = str(out / (name + ".png"))
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)

take("STYLE_03_balcony_street_check", (290, -1050, 470), (155, -320, 400), 490)
take("STYLE_03_balcony_plan_check", (300, -600, 950), (155, -325, 385), 510)
