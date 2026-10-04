"""Assign an independent art style to all 18 existing geometry lots.

This preserves the lot footprint, roof geometry family, seed, shared walls,
points and existing PCG graphs. It is safe to run before replacing modules.
"""
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
STYLE_MAP = json.loads((ROOT / "Pipeline/Unreal/visual_style_map.json").read_text(encoding="utf-8"))
CATALOG = "/Game/Mazzarino80/PCG/DA_Buildings_Test18"
asset = unreal.EditorAssetLibrary.load_asset(CATALOG)
if not asset:
    raise RuntimeError("Missing building catalog: " + CATALOG)
buildings = list(asset.get_editor_property("buildings"))
ids = {str(building.get_editor_property("building_id")) for building in buildings}
if ids != set(STYLE_MAP) or len(buildings) != 18:
    raise RuntimeError("Style map must cover precisely the 18 existing lots")
before = {}
for building in buildings:
    lot = str(building.get_editor_property("building_id"))
    before[lot] = str(building.get_editor_property("visual_style"))
    building.set_editor_property("visual_style", STYLE_MAP[lot])
asset.modify()
asset.set_editor_property("buildings", buildings)
if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
    raise RuntimeError("Could not save style assignment")
reloaded = unreal.EditorAssetLibrary.load_asset(CATALOG)
after = {str(b.get_editor_property("building_id")): str(b.get_editor_property("visual_style"))
         for b in reloaded.get_editor_property("buildings")}
if after != STYLE_MAP:
    raise RuntimeError("Saved style map differs from requested map: " + repr(after))
out = {"catalog": CATALOG, "lot_count": len(after), "before": before, "after": after,
       "pcg_geometry_changed": False}
(ROOT / "Pipeline/Unreal/all_visual_style_assignment.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print("M80_ALL_STYLES_SAVED", len(after))
