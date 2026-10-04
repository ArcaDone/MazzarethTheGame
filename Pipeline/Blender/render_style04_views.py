"""Street/courtyard/roof visual checks for the courtyard pilot."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
scene = bpy.context.scene
for collection in bpy.data.collections:
    if collection.name.startswith("QA_STYLE_"):
        collection.hide_render = collection.name != "QA_STYLE_04_1249069228"
cam = bpy.data.objects["QA_Street_50mm"]
scene.camera = cam
scene.render.resolution_x = 1280
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
for label, location, target, lens in (
    ("courtyard", (39.0, -4.75, 1.70), (39.0, -.10, 2.65), 28),
    ("roof", (46.5, -4.5, 11.0), (39.0, 1.80, 6.20), 40),
):
    cam.data.lens = lens
    cam.location = location
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(BLEND.parent / ("STYLE_04_" + label + ".png"))
    bpy.ops.render.render(write_still=True)
    print("M80_VIEW", label, scene.render.filepath)
