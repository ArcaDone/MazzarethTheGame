"""Small read-only audit of supplementary doors, fence, pots and balcony."""
import json
import os
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(r"D:\Blender")
OUT = Path(__file__).resolve().parent / "output/mazzarino_source_inventory/extra_candidates.json"
paths = [
    ROOT / "DioramaAssets/Balcony.blend",
    ROOT / "DioramaAssets/assets/models/cast_iron_fence_45f70b96-c031-4860-8109-500ed9a48870/cast_iron_fence_2614fda1-c7bf-406b-a3b1-61a8c278d33f.blend",
    ROOT / "DioramaAssets/assets/models/plant_pot_big_b6a53708-55d4-4a1c-961e-deedec48715a/plant_pot_big_b55462e8-62e8-4ae8-b5cc-8faa74de4885.blend",
    ROOT / "AssetsMazzarethTheGame/TestBuildingParts/assets/models/old-italian-fron_f6331acb-c598-4b5e-8a90-816d4dc9187c/old-italian-front-door_2K_3fbca813-2f73-4241-bb27-0c35a116eb01.blend",
]
report = {}
for path in paths:
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    objects = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        pts = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        dims = [round(max(p[i] for p in pts) - min(p[i] for p in pts), 4)
                for i in range(3)]
        objects.append({"name": obj.name, "faces": len(obj.data.polygons),
                        "dimensions_m": dims,
                        "materials": [m.name if m else None for m in obj.data.materials]})
    images = []
    for im in bpy.data.images:
        if im.source != "FILE":
            continue
        resolved = bpy.path.abspath(im.filepath, library=im.library)
        images.append({"name": im.name, "packed": bool(im.packed_file),
                       "exists": os.path.isfile(resolved), "path": resolved})
    report[str(path)] = {"objects": objects, "images": images}
    print("M80_EXTRA", path.name, "objects", len(objects), "faces",
          sum(o["faces"] for o in objects), "missing_images",
          sum(not im["packed"] and not im["exists"] for im in images))
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
