"""Check curated meshes, materials, dimensions and packed active textures."""
import json
from pathlib import Path
import bpy

OUT = Path(__file__).resolve().parent / "output/mazzarino_reuse_kit_v1"
manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
bpy.ops.wm.open_mainfile(filepath=str(OUT / "Mazzarino_Reuse_Kit_v1.blend"), load_ui=False)
issues = []
rows = []
for entry in manifest["objects"]:
    obj = bpy.data.objects.get(entry["name"])
    if not obj or obj.type != "MESH":
        issues.append(entry["name"] + ": missing mesh")
        continue
    if len(obj.data.polygons) != entry["faces"]:
        issues.append(entry["name"] + ": face count changed")
    if not obj.data.materials:
        issues.append(entry["name"] + ": no materials")
    if any(mat is None for mat in obj.data.materials):
        issues.append(entry["name"] + ": empty material slot")
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type != "TEX_IMAGE" or not node.image:
                continue
            if not any(output.links for output in node.outputs):
                continue
            image = node.image
            if not image.packed_file and not Path(bpy.path.abspath(image.filepath)).is_file():
                issues.append(entry["name"] + ": missing " + image.name)
    expected = entry["dimensions_m"]
    if min(expected) <= 0.001:
        issues.append(entry["name"] + ": degenerate dimensions")
    rows.append({"name": obj.name, "faces": len(obj.data.polygons),
                 "materials": len(obj.data.materials), "role": obj.get("pcg_role")})
for name in ("PILOT__KIT_Balcony_StoneAndIron_350", "B80__Porta6", "B80__Tetto"):
    item = next((x for x in manifest["objects"] if x["name"] == name), None)
    if not item:
        issues.append(name + ": required module missing")
        continue
    width = item["dimensions_m"][0]
    if name.startswith("PILOT") and not 3.3 <= width <= 3.7:
        issues.append(name + ": balcony width out of range")
    if name == "B80__Porta6" and not 2.4 <= item["dimensions_m"][2] <= 2.8:
        issues.append(name + ": door height out of range")

result = {"blender": bpy.app.version_string, "objects_checked": len(rows),
          "faces_total": sum(x["faces"] for x in rows), "issues": issues,
          "passed": not issues}
(OUT / "validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_KIT_VALIDATION", json.dumps(result))
if issues:
    raise SystemExit(2)
