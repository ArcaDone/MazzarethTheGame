"""Check selected Comune garments before using them in the Blender pilot."""
from pathlib import Path
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "Pipeline/Unreal/comune_geometry_review"
for name in ("clothes_favela__SM_Clothes_01.fbx", "clothes_favela__SM_Clothes_03.fbx",
             "clothes_middleeast__SM_clothes_B_02.fbx"):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(DIR / name))
    records = []
    for obj in bpy.context.selected_objects:
        if obj.type != "MESH":
            continue
        box = [(obj.matrix_world @ __import__("mathutils").Vector(c)) for c in obj.bound_box]
        records.append({"name": obj.name, "polygons": len(obj.data.polygons),
                        "min": [min(v[i] for v in box) for i in range(3)],
                        "max": [max(v[i] for v in box) for i in range(3)],
                        "materials": [m.name if m else None for m in obj.data.materials]})
    print("CLOTHES_FBX", name, json.dumps(records))
