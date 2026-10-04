"""Report image dependencies on likely reusable Mazzarino modules."""
import json
import os
from pathlib import Path
import bpy

ROOT = Path(r"D:\Blender\AssetsMazzarethTheGame")
OUT = Path(__file__).resolve().parent / "output/mazzarino_source_inventory"
PICK = {
    "CaseSoluzione": ["Ground.000", "Ground.001", "Ground.008", "Ground.011",
                      "wall_001", "wall_002", "wall_003", "wall_004", "wall_005",
                      "wall_006", "wall_010", "wall_011", "wall_012", "wall_013"],
    "balcony_80s": ["Ground.000", "Ground.001", "Ground.011", "Balcony2", "Porta4",
                    "Porta6", "Tetto", "roof", "tegole", "trimm", "lampione2",
                    "small_chimney_round", "antenna"],
    "case_evy": ["Ivy_Instance_1_old", "Ivy_Instance_2_old", "esperiemnto", "low219"],
}

report = {}
for name, picks in PICK.items():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / (name + ".blend")), load_ui=False)
    rows = []
    for object_name in picks:
        obj = bpy.data.objects.get(object_name)
        if not obj:
            rows.append({"name": object_name, "missing_object": True})
            continue
        materials = []
        for material in obj.data.materials:
            if not material:
                continue
            images = []
            if material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type != "TEX_IMAGE" or not node.image:
                        continue
                    image = node.image
                    path = bpy.path.abspath(image.filepath, library=image.library)
                    images.append({"name": image.name, "path": path,
                                   "packed": bool(image.packed_file),
                                   "exists": os.path.isfile(path)})
            materials.append({"name": material.name, "images": images})
        rows.append({"name": object_name, "faces": len(obj.data.polygons),
                     "materials": materials})
    report[name] = rows
    print("M80_DEPS", name, json.dumps(rows))
(OUT / "selected_materials.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
