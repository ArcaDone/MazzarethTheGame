"""Street-level scale check assembled only from reusable kit modules."""
from pathlib import Path
import math
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent / "output/mazzarino_reuse_kit_v1"
bpy.ops.wm.open_mainfile(filepath=str(OUT / "Mazzarino_Reuse_Kit_v1.blend"), load_ui=False)
scene = bpy.context.scene
for obj in bpy.data.objects:
    if "pcg_role" in obj:
        obj.hide_render = True

assembly = bpy.data.collections.new("QA_Assembly_6m_StreetLevel")
scene.collection.children.link(assembly)

def add(source, location, name):
    template = bpy.data.objects[source]
    instance = bpy.data.objects.new(name, template.data)
    assembly.objects.link(instance)
    instance.location = location
    return instance

# Two 3m facade bays. The whole sample is only an attachment and scale check;
# it does not duplicate the four-styles reference building.
add("B80__Ground.002", (-1.5, 0.0, 0.0), "QA_Ground_DoorBay")
add("B80__Ground.003", (1.5, 0.0, 0.0), "QA_Ground_PlainBay")
add("B80__Porta6", (-1.5, 0.02, 0.0), "QA_Door")
add("CS__wall_004", (-1.5, 0.0, 3.0), "QA_Upper_WindowLeft")
add("CS__wall_010", (1.5, 0.0, 3.0), "QA_Upper_WindowRight")
add("PILOT__KIT_Balcony_StoneAndIron_350", (-1.5, -0.46, 2.3), "QA_Balcony")
add("B80__Tetto", (0.0, 3.0, 6.0), "QA_Roof")
add("B80__small_chimney_round", (1.8, 1.2, 7.2), "QA_Chimney")
add("PROP__PottedPlant_Small_01", (-2.8, -1.2, 3.35), "QA_BalconyPot")
add("EVY__Ivy_Instance_1_old_WALL", (2.55, -0.64, 3.15), "QA_WallIvy")

# 1.80m neutral person proxy, for a direct visual scale comparison.
mat = bpy.data.materials.new("QA_Matte_Mannequin")
mat.diffuse_color = (0.20, 0.24, 0.26, 1)
for part, loc, scale in [
    ("body", (0, -3.1, 1.05), (0.23, 0.14, 0.48)),
    ("head", (0, -3.1, 1.64), (0.13, 0.13, 0.16)),
    ("leg_l", (-0.10, -3.1, 0.37), (0.09, 0.10, 0.37)),
    ("leg_r", (0.10, -3.1, 0.37), (0.09, 0.10, 0.37)),
]:
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    obj = bpy.context.object
    obj.name = "QA_180cm_" + part
    obj.scale = scale
    obj.data.materials.append(mat)
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    assembly.objects.link(obj)

# Ground only for judging attachment; no decorative terrain masking gaps.
ground_mat = bpy.data.materials.new("QA_Ground_Neutral")
ground_mat.diffuse_color = (0.33, 0.31, 0.28, 1)
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, -0.02))
ground = bpy.context.object
ground.name = "QA_Ground"
ground.scale = (8, 7, 1)
ground.data.materials.append(ground_mat)

world = bpy.data.worlds.new("QA_World")
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs["Color"].default_value = (0.55, 0.62, 0.72, 1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.8
scene.world = world

sun_data = bpy.data.lights.new("QA_Sun", "SUN")
sun_data.energy = 2.1
sun = bpy.data.objects.new("QA_Sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(28), math.radians(-26), math.radians(-20))

cam_data = bpy.data.cameras.new("QA_Camera_Street")
cam = bpy.data.objects.new("QA_Camera_Street", cam_data)
scene.collection.objects.link(cam)
cam.location = (8.7, -17.5, 7.3)
target = Vector((0.0, 0.3, 3.9))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_data.type = "ORTHO"
cam_data.ortho_scale = 11.3
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 1500
scene.render.resolution_y = 1250
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "assembly_scale_check.png")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Mazzarino_Reuse_Assembly_QA.blend"), compress=True)
bpy.ops.render.render(write_still=True)
print("M80_ASSEMBLY_PREVIEW", scene.render.filepath)
