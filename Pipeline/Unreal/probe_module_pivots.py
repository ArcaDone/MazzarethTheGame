"""Measure imported module origins against the assembled stage for PCG transforms."""
from pathlib import Path
import json
import unreal

ROOT = Path(__file__).resolve().parents[2]
paths = [
    "/Game/Mazzarino80/ReuseKit/Modules/SM_M80_B80__Tetto",
    "/Game/Mazzarino80/ReuseKit/PilotStages/SM_M80_QA_STYLE_01_1249069204_Roofs",
    "/Game/Mazzarino80/ReuseKit/Modules/SM_M80_B80__Ground_002",
    "/Game/Mazzarino80/ReuseKit/Modules/SM_M80_FENCE__Cast_Iron_Fence_09",
    "/Game/Mazzarino80/ReuseKit/Modules/SM_M80_FENCE__Cast_Iron_Fence_09_LOD1",
    "/Game/Mazzarino80/ReuseKit/Modules/SM_M80_PILOT__KIT_Balcony_StoneAndIron_350",
    "/Game/Mazzarino80/ReuseKit/Modules/SM_M80_PROP__PottedPlant_Small_01",
    "/Game/Mazzarino80/ReuseKit/Modules/SM_M80_B80__small_chimney_round",
    "/Game/Mazzarino80/ReuseKit/PilotStages/SM_M80_QA_STYLE_01_1249069204_Facades",
]
records = []
for path in paths:
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("Missing mesh: " + path)
    bounds = mesh.get_bounds()
    records.append({"asset": path,
                    "origin_cm": [getattr(bounds.origin, axis) for axis in ("x", "y", "z")],
                    "extent_cm": [getattr(bounds.box_extent, axis) for axis in ("x", "y", "z")]})
(ROOT / "Pipeline/Unreal/module_pivot_probe.json").write_text(
    json.dumps(records, indent=2), encoding="utf-8")
print("M80_MODULE_PIVOTS", len(records))
