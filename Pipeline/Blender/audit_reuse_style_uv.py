"""Report missing or collapsed UV faces in the four Blender review assemblies."""
from pathlib import Path
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
OUT = BLEND.with_name("uv_audit.json")
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)

results = []
for obj in bpy.data.objects:
    if obj.type != "MESH" or not any(c.name.startswith("QA_STYLE_") for c in obj.users_collection):
        continue
    if obj.get("pcg_role") == "scale_reference":
        continue
    mesh = obj.data
    uv = next((layer for layer in mesh.uv_layers if layer.active_render), None)
    textured = {i for i, mat in enumerate(mesh.materials)
                if mat and mat.use_nodes and any(n.type == "TEX_IMAGE" for n in mat.node_tree.nodes)}
    if not textured:
        continue
    if uv is None:
        results.append({"object": obj.name, "issue": "missing_render_uv", "faces": len(mesh.polygons)})
        continue
    collapsed = []
    collapsed_materials = {}
    for poly in mesh.polygons:
        if poly.material_index not in textured or poly.area < .001:
            continue
        coords = [uv.data[i].uv for i in poly.loop_indices]
        uv_area = abs(sum(coords[i].x * coords[(i + 1) % len(coords)].y -
                          coords[(i + 1) % len(coords)].x * coords[i].y
                          for i in range(len(coords)))) * .5
        if uv_area < 1e-8:
            collapsed.append(poly.index)
            material_name = mesh.materials[poly.material_index].name
            collapsed_materials[material_name] = collapsed_materials.get(material_name, 0) + 1
    if collapsed:
        results.append({"object": obj.name, "issue": "collapsed_uv", "faces": collapsed[:20],
                        "count": len(collapsed), "materials": collapsed_materials})

summary = {"blend": str(BLEND), "objects_checked": sum(
    obj.type == "MESH" and any(c.name.startswith("QA_STYLE_") for c in obj.users_collection)
    for obj in bpy.data.objects), "issues": results}
OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("UV_AUDIT", json.dumps({"objects_checked": summary["objects_checked"],
                              "issue_objects": len(results), "output": str(OUT)}))
