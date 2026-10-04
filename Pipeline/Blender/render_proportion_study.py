"""Temporary STYLE_03 silhouette studies; the saved kit is not modified."""
from pathlib import Path
import bpy
from mathutils import Matrix

out = Path(__file__).resolve().parent / "output/style03_reference_v2"
bpy.ops.wm.open_mainfile(filepath=str(out / "Mazzarino_STYLE_03_Reference_Gate_v2.blend"))
scene = bpy.context.scene
camera = bpy.data.objects.get("ScaleAudit_42mm_EyeHeight170cm")
scene.camera = camera
scene.render.engine = "CYCLES"
scene.cycles.samples = 42
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
members = [obj for obj in bpy.data.objects if obj.get("module_type")
           and obj.get("module_type") not in {"scale_mannequin_180cm", "scale_ruler"}]
original = [(obj, obj.matrix_world.copy()) for obj in members]
root = bpy.data.objects.new("TEMP_ProportionStudy", None)
scene.collection.objects.link(root)
for obj in members:
    obj.parent = root
    obj.matrix_parent_inverse = Matrix.Identity(4)
for obj in bpy.data.objects:
    if obj.get("module_type") == "scale_mannequin_180cm":
        obj.hide_render = False

for name, x_scale, z_scale in (("narrow_085_tall_115", .85, 1.15),
                               ("narrow_090_tall_115", .90, 1.15)):
    root.scale = (x_scale, 1, z_scale)
    bpy.context.view_layer.update()
    scene.render.filepath = str(out / ("STYLE_03_study_" + name + ".png"))
    bpy.ops.render.render(write_still=True)

root.scale = (1, 1, 1)
bpy.context.view_layer.update()
for obj, matrix in original:
    obj.parent = None
    obj.matrix_world = matrix
bpy.data.objects.remove(root, do_unlink=True)
