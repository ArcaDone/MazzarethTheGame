"""Report source and assembled bounds for the four review buildings."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
OUT = BLEND.with_name("assembly_bounds_audit.json")
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
names = ["B80__Tetto", "B80__Ground.002", "B80__wall_000.001",
         "STYLE_01_Roof", "STYLE_01_Ground_0", "STYLE_01_Ground_1",
         "STYLE_01_left_0_0", "STYLE_01_left_0_1", "STYLE_01_Rear_0_0",
         "STYLE_01_Balcony_1_0", "STYLE_01_Door", "STYLE_04_CourtWall_Left",
         "STYLE_04_CourtWall_ReturnLeft", "STYLE_04_Gate_Candidate"]
result = []
for name in names:
    obj = bpy.data.objects[name]
    verts = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = [round(min(v[i] for v in verts), 3) for i in range(3)]
    high = [round(max(v[i] for v in verts), 3) for i in range(3)]
    result.append({"name": name, "min": low, "max": high,
                   "location": [round(x, 3) for x in obj.location],
                   "scale": [round(x, 3) for x in obj.scale]})
OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("ASSEMBLY_BOUNDS_AUDIT", OUT)
