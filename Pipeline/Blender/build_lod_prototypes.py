"""Non-destructive LOD trial for repeated architectural details."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
OUT = SOURCE.parent / "lod_review"
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
scene = bpy.context.scene

targets = {
    "STYLE_01_Roof": .38,
    "STYLE_01_Door": .35,
    "STYLE_02_Door": .35,
    "STYLE_02_Balcony_1_0": .34,
    "STYLE_02_Balcony_1_1": .34,
    "STYLE_03_Door": .35,
    "STYLE_04_Roof": .38,
    "STYLE_04_Door": .35,
    "STYLE_04_Gate_Candidate": .36,
}

def tris(mesh):
    return sum(len(face.vertices) - 2 for face in mesh.polygons)

records = []
for name, ratio in targets.items():
    original = bpy.data.objects[name]
    duplicate = original.copy()
    duplicate.data = original.data.copy()
    duplicate.name = name + "__LOD1_TRIAL"
    original.users_collection[0].objects.link(duplicate)
    bpy.ops.object.select_all(action="DESELECT")
    duplicate.select_set(True)
    bpy.context.view_layer.objects.active = duplicate
    modifier = duplicate.modifiers.new("GeometryLOD1", "DECIMATE")
    modifier.ratio = ratio
    before = tris(original.data)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    after = tris(duplicate.data)
    duplicate["lod_source"] = name
    duplicate["lod_ratio"] = ratio
    duplicate["pcg_role"] = original.get("pcg_role", "detail")
    original.hide_render = True
    records.append({"name": name, "before_triangles": before,
                    "lod1_triangles": after, "reduction_percent": round((1 - after / before) * 100, 1)})

scene.camera = bpy.data.objects["QA_Street_50mm"]
for index, style in ((0, "STYLE_01"), (1, "STYLE_02"), (3, "STYLE_04")):
    x = index * 13.0
    camera = scene.camera
    camera.location = (x + 9.5, -16.5, 7.0)
    target = Vector((x, 1.8, 3.0))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    for collection in bpy.data.collections:
        if collection.name.startswith("QA_STYLE_"):
            collection.hide_render = not collection.name.startswith("QA_" + style)
    scene.render.filepath = str(OUT / f"{style}_LOD1.png")
    bpy.ops.render.render(write_still=True)

for collection in bpy.data.collections:
    if collection.name.startswith("QA_STYLE_"):
        collection.hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Mazzarino_LOD1_TRIAL.blend"), compress=True)
(OUT / "lod1_audit.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
print("M80_LOD1_DONE", OUT)
