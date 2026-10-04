"""Extract the small shared texture set from the reviewed Blender scene."""
from pathlib import Path
import json
import shutil

import bpy

ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
OUT = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/unreal_export/textures"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)

NAMES = {
    "StoneWall": "T_M80_Limestone_Generated_v1.png",
    "StoneFormal": "T_M80_stone_formal",
    "PlasterWarm": "T_M80_Plaster_Warm_Generated_v1.png",
    "OldWood": "T_M80_wood",
    "Iron": "T_M80_iron",
    "Terracotta": "T_M80_terracotta",
    "StoneTrim": "T_M80_stone",
    "Glass": "T_M80_glass",
}
records = []
for role, name in NAMES.items():
    image = bpy.data.images.get(name)
    if image is None:
        raise RuntimeError("Missing packed material image: " + name)
    if not image.has_data:
        image.reload()
    path = OUT / f"T_M80_Reuse_{role}.png"
    if image.has_data:
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
    else:
        original = Path(bpy.path.abspath(image.filepath))
        if not original.is_file():
            raise RuntimeError("Image unavailable: " + name + " from " + str(original))
        shutil.copyfile(original, path)
    records.append({"role": role, "source": name, "file": str(path),
                    "size": list(image.size), "bytes": path.stat().st_size})
(OUT / "texture_manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
print("M80_SHARED_TEXTURES", len(records), OUT)
