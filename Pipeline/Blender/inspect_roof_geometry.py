"""Read-only statistics for the existing reusable tiled roof."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "Pipeline/Blender/output/mazzarino_reuse_kit_v1/Mazzarino_Reuse_Kit_v1.blend"
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
obj = bpy.data.objects["B80__Tetto"]
mesh = obj.data
stats = defaultdict(lambda: {"count": 0, "zmin": 100000.0, "zmax": -100000.0,
                             "sample_centers": []})
for face in mesh.polygons:
    item = stats[face.material_index]
    item["count"] += 1
    item["zmin"] = min(item["zmin"], face.center.z)
    item["zmax"] = max(item["zmax"], face.center.z)
    if len(item["sample_centers"]) < 8:
        item["sample_centers"].append([round(v, 3) for v in face.center])
report = {"faces": len(mesh.polygons), "verts": len(mesh.vertices),
          "materials": [m.name if m else None for m in mesh.materials],
          "by_material": stats}
for x, y in ((1.5, -.8), (1.5, -1.8), (2.4, -1.8), (0, -1.8)):
    close = [v.co.z for v in mesh.vertices
             if abs(v.co.x - x) < .18 and abs(v.co.y - y) < .18]
    report[f"surface_{x}_{y}"] = {"samples": len(close), "highest": max(close) if close else None}
print("ROOF_GEOMETRY", json.dumps(report))
