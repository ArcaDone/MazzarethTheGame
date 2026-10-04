"""Render an actual-shape review of the Comune clothes candidates."""
from pathlib import Path
import math
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Pipeline/Unreal/comune_geometry_review"
structure = "--structure" in sys.argv
OUT = SOURCE / ("structure_shape_review.png" if structure else "clothes_shape_review.png")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

mat = bpy.data.materials.new("QA_Clothes_Neutral")
mat.diffuse_color = (.55, .42, .30, 1)
text_mat = bpy.data.materials.new("QA_Label")
text_mat.diffuse_color = (.08, .08, .08, 1)

if structure:
    names = {"SM_stairs_01", "SM_Old_Stair_01", "SM_Old_Stair_02", "SM_Rain_Pipe_01",
             "SM_awning_01", "SM_metal_fence_01", "SM_Windows_grill_01",
             "SM_Metal_Fence_02", "SM_wooden_beams_01"}
    files = [p for p in sorted(SOURCE.glob("*.fbx")) if p.stem.split("__")[-1] in names]
    assert len(files) == 9, files
else:
    files = sorted(SOURCE.glob("clothes_*__*.fbx"))
    assert len(files) == 10, files
for index, path in enumerate(files):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_custom_normals=False)
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not imported:
        continue
    minc = [min((o.matrix_world @ Vector(c))[a] for o in imported for c in o.bound_box)
            for a in range(3)]
    maxc = [max((o.matrix_world @ Vector(c))[a] for o in imported for c in o.bound_box)
            for a in range(3)]
    extent = [maxc[a] - minc[a] for a in range(3)]
    center = [(minc[a] + maxc[a]) / 2 for a in range(3)]
    # Rotate the broad dimension into the viewing plane. Preserve size: the
    # 1.8 m grid and label make wrong-scale candidates immediately visible.
    turn = math.pi / 2 if extent[1] > extent[0] else 0
    cols = 3 if structure else 5
    xstep = 3.6 if structure else 2.6
    zstep = 3.1 if structure else 2.7
    xcell = (index % cols) * xstep
    zcell = ((2 if structure else 1) - index // cols) * zstep
    display_scale = min(2.8 / max(extent[0], extent[1], .01),
                        2.0 / max(extent[2], .01), 1.0) if structure else 1.0
    for obj in imported:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)
        obj.rotation_euler.z += turn
        obj.scale *= display_scale
        # Most imported meshes are authored in centimetres; importer handles
        # the factor and this move only recentres the FBX geometry.
        offset = Vector((obj.location.x - center[0], obj.location.y - center[1],
                         obj.location.z - minc[2]))
        obj.location = Vector((xcell, 0, zcell)) + offset
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    bpy.ops.object.text_add(location=(xcell - 1.45 if structure else xcell - 1.05, -.15, zcell - .27))
    label = bpy.context.object
    label.data.body = path.stem.split("__")[-1].replace("SM_", "")
    label.data.size = .15
    label.data.materials.append(text_mat)
    label.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.text_add(location=(xcell - 1.45 if structure else xcell - 1.05, -.15, zcell - .46))
    dimensions = bpy.context.object
    dimensions.data.body = "%.0f x %.0f x %.0f cm" % tuple(v * 100 for v in extent)
    dimensions.data.size = .12
    dimensions.data.materials.append(text_mat)
    dimensions.rotation_euler = (math.pi / 2, 0, 0)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"
scene.display.shading.curvature_ridge_factor = 1.5
scene.render.resolution_x = 1800 if structure else 2200
scene.render.resolution_y = 1700 if structure else 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT)
bpy.ops.object.camera_add(location=(3.6 if structure else 5.2, -30, 4.2 if structure else 2.0))
camera = bpy.context.object
camera.rotation_euler = (Vector((3.6 if structure else 5.2, 0, 4.2 if structure else 2.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 12.0 if structure else 15.0
scene.camera = camera
bpy.ops.render.render(write_still=True)
print("CLOTHES_SHAPE_REVIEW", OUT)
