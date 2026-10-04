"""Render category previews for a Blender kit without changing its source file."""
from pathlib import Path
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent / "output/mazzarino_reuse_kit_v1"
bpy.ops.wm.open_mainfile(filepath=str(OUT / "Mazzarino_Reuse_Kit_v1.blend"), load_ui=False)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 1600
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
if scene.world is None:
    scene.world = bpy.data.worlds.new("Kit_Inspection_World")
scene.world.color = (0.48, 0.48, 0.48)

camera_data = bpy.data.cameras.new("Kit_Inspection_Ortho")
camera = bpy.data.objects.new("Kit_Inspection_Ortho", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 27
camera.location = (10.8, -42, 3.0)
camera.rotation_euler = (Vector((10.8, 0, 3.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()

sun_data = bpy.data.lights.new("Kit_Inspection_Sun", "SUN")
sun_data.energy = 2.0
sun = bpy.data.objects.new("Kit_Inspection_Sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (0.45, -0.35, -0.25)

roles = {
    "facades_ground": {"facade_ground"},
    "facades_upper": {"facade_upper", "facade_upper_candidate"},
    "details": {"door", "balcony", "roof", "roof_trim", "corner", "chimney",
                "ivy_cluster", "ivy_wall", "detail", "roof_detail"},
    "featured_additions": {"gate_candidate", "door_scan_candidate",
                            "potted_plant", "ivy_wall"},
}
for filename, visible in roles.items():
    for obj in bpy.data.objects:
        if "pcg_role" in obj:
            obj.hide_render = obj["pcg_role"] not in visible
    if filename == "facades_ground":
        camera.location = (10.8, -42, -1.0)
        camera_data.ortho_scale = 27
    elif filename == "facades_upper":
        camera.location = (10.8, -42, 4.5)
        camera_data.ortho_scale = 27
    elif filename == "details":
        camera.location = (12.0, -42, -13.0)
        camera_data.ortho_scale = 32
    else:
        showcase = {
            "FENCE__Cast Iron Fence 09": (-5.0, 0.0, 0.0),
            "FENCE__Cast Iron Fence 09_LOD1": (-2.0, 0.0, 0.0),
            "DOOR__OldItalian_Front_01": (2.0, 0.0, 0.0),
            "PROP__PottedPlant_Small_01": (5.0, 0.0, 0.0),
            "EVY__Ivy_Instance_1_old_WALL": (6.4, 0.0, 0.3),
            "EVY__Ivy_Instance_2_old_WALL": (7.4, 0.0, 0.3),
        }
        for name, location in showcase.items():
            obj = bpy.data.objects.get(name)
            if obj:
                obj.location = location
        camera.location = (1.0, -24.0, 1.65)
        camera_data.ortho_scale = 16
    target = Vector((camera.location.x, 0, camera.location.z))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / (filename + ".png"))
    bpy.ops.render.render(write_still=True)
    print("M80_PREVIEW", filename, scene.render.filepath)
