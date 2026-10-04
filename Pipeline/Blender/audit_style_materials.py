"""Audit final visible pilot meshes for missing material and texture slots."""
from pathlib import Path
import json
import os
import bpy

ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
OUT = BLEND.with_name("material_audit.json")
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)

issues = []
materials = {}
for obj in bpy.data.objects:
    if obj.type != "MESH" or not obj.name.startswith("STYLE_"):
        continue
    if obj.hide_render or obj.name.startswith("QA_"):
        continue
    if not obj.data.materials:
        issues.append({"object": obj.name, "problem": "no material slots"})
    for face in obj.data.polygons:
        if face.material_index >= len(obj.data.materials) or obj.data.materials[face.material_index] is None:
            issues.append({"object": obj.name, "problem": "face has empty material slot"})
            break
    for material in obj.data.materials:
        if not material or material.name in materials:
            continue
        row = {"name": material.name, "images": [], "roughness": [], "metallic": []}
        if material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    image = node.image
                    path = bpy.path.abspath(image.filepath, library=image.library)
                    row["images"].append({"image": image.name, "path": path,
                                          "packed": bool(image.packed_file),
                                          "exists": bool(image.packed_file or os.path.isfile(path))})
                    if not row["images"][-1]["exists"]:
                        issues.append({"material": material.name, "problem": "missing texture", "path": path})
                elif node.type == "BSDF_PRINCIPLED":
                    for key in ("Roughness", "Metallic"):
                        sock = node.inputs.get(key)
                        if sock and not sock.is_linked:
                            row[key.lower()].append(float(sock.default_value))
        materials[material.name] = row

report = {"blend": str(BLEND), "visible_materials": list(materials.values()),
          "issues": issues, "technical_pass": len(issues) == 0}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("STYLE_MATERIAL_AUDIT", "materials", len(materials), "issues", len(issues), OUT)
