"""Count scene geometry so PCG repetition is not designed blind."""
from pathlib import Path
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
OUT = BLEND.with_name("geometry_audit.json")
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)

rows = []
for collection in bpy.data.collections:
    if not collection.name.startswith("QA_STYLE_"):
        continue
    items = []
    for obj in collection.objects:
        if obj.type != "MESH" or obj.name.startswith("QA_"):
            continue
        mesh = obj.data
        triangles = sum(len(face.vertices) - 2 for face in mesh.polygons)
        items.append({"object": obj.name, "role": obj.get("pcg_role"), "triangles": triangles,
                      "materials": len([m for m in mesh.materials if m]),
                      "source_module": obj.get("source_module")})
    rows.append({"collection": collection.name, "objects": len(items),
                 "triangles": sum(x["triangles"] for x in items),
                 "high_cost": sorted(items, key=lambda x: x["triangles"], reverse=True)[:12]})
OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print("STYLE_GEOMETRY_AUDIT", [(x["collection"], x["triangles"]) for x in rows], OUT)
