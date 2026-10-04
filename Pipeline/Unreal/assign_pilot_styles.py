"""Record art-direction identity on the four existing PCG pilot lots.

Run only after MazzarinoRoads is rebuilt with FBuildingData.VisualStyle.
This does not replace meshes or regenerate buildings; the visual gate in
Blender controls when the PCG graphs may begin consuming the new kit.
"""
import json
from pathlib import Path

import unreal

STYLE_BY_LOT = {
    "1249069204": "STYLE_01",
    "1249068307": "STYLE_02",
    "1249069200": "STYLE_03",
    "1249069228": "STYLE_04",
}
PATH = "/Game/Mazzarino80/PCG/DA_Buildings_Test18"
asset = unreal.EditorAssetLibrary.load_asset(PATH)
if not asset:
    raise RuntimeError("Catalog missing: " + PATH)
buildings = list(asset.get_editor_property("buildings"))
seen = set()
for building in buildings:
    lot = str(building.get_editor_property("building_id"))
    if lot in STYLE_BY_LOT:
        building.set_editor_property("visual_style", STYLE_BY_LOT[lot])
        seen.add(lot)
if seen != set(STYLE_BY_LOT):
    raise RuntimeError("Missing pilot lots: " + repr(set(STYLE_BY_LOT) - seen))
asset.set_editor_property("buildings", buildings)
if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
    raise RuntimeError("Unable to save PCG catalog")
out = Path(__file__).resolve().parent / "pilot_style_assignment.json"
out.write_text(json.dumps({"catalog": PATH, "style_by_lot": STYLE_BY_LOT,
                           "all_18_lots_preserved": len(buildings) == 18,
                           "building_count": len(buildings)}, indent=2), encoding="utf-8")
print("M80_PILOT_STYLES_SAVED", str(out))
