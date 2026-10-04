"""Locate degenerate triangles/tangents before spreading modules through PCG."""
from pathlib import Path
import json

import bpy

ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
OUT = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/unreal_export/geometry_findings.json"
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)

rows = []
for obj in bpy.data.objects:
    if obj.type != "MESH" or "pcg_role" not in obj:
        continue
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = next((layer for layer in mesh.uv_layers if layer.active_render), None)
    geometry_bad = 0
    uv_bad = 0
    for tri in mesh.loop_triangles:
        a, b, c = (mesh.vertices[i].co for i in tri.vertices)
        if (b-a).cross(c-a).length < 1e-8:
            geometry_bad += 1
        if uv:
            u, v, w = (uv.data[i].uv for i in tri.loops)
            area = abs((v.x-u.x)*(w.y-u.y) - (v.y-u.y)*(w.x-u.x))
            if area < 1e-9:
                uv_bad += 1
    if geometry_bad or uv_bad:
        rows.append({"object": obj.name, "source": obj.get("source_module", obj.name),
                     "triangles": len(mesh.loop_triangles), "zero_geometry": geometry_bad,
                     "zero_uv": uv_bad})

rows.sort(key=lambda row: row["zero_geometry"] + row["zero_uv"], reverse=True)
OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print("M80_DEGENERATE_AUDIT", len(rows), "objects", OUT)
