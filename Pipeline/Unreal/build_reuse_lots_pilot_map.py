"""Duplicate the irregular-lot map and switch four or all lots to kit candidates."""
from pathlib import Path
import json
import os

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_Validation"
ALL_LOTS = os.environ.get("M80_REUSE_QA_ALL_LOTS") == "1"
TARGET = ("/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_18Lots_QA" if ALL_LOTS
          else "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_4Lots_QA")
PILOTS = (tuple(json.loads((ROOT / "Pipeline/Unreal/visual_style_map.json").read_text(encoding="utf-8")))
          if ALL_LOTS else ("1249069204", "1249068307", "1249069200", "1249069228"))
if not unreal.EditorAssetLibrary.does_asset_exist(TARGET):
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET):
        raise RuntimeError("Could not duplicate irregular-lot validation map")
world = unreal.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:
    raise RuntimeError("Could not load " + TARGET)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
existing = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
records = []
for lot in PILOTS:
    label = "BP_ProceduralBuilding_" + lot
    source = existing.get(label)
    if not isinstance(source, unreal.PCGVolume):
        raise RuntimeError("Missing PCG lot volume " + label)
    location = source.get_actor_location()
    rotation = source.get_actor_rotation()
    scale = source.get_actor_scale3d()
    graph_path = "/Game/Mazzarino80/ReuseKit/PCG/Lots/PCG_Building_" + lot
    graph = unreal.EditorAssetLibrary.load_asset(graph_path)
    if not isinstance(graph, unreal.PCGGraph):
        raise RuntimeError("Missing candidate lot graph " + graph_path)
    actors.destroy_actor(source)
    replacement = actors.spawn_actor_from_class(unreal.PCGVolume, location, rotation)
    replacement.set_actor_label("Reuse Candidate " + lot)
    replacement.set_actor_scale3d(scale)
    component = replacement.get_component_by_class(unreal.PCGComponent)
    if component is None:
        raise RuntimeError("Replacement volume has no PCG component")
    component.set_graph(graph)
    records.append({"lot": lot, "graph": graph_path,
                    "location_cm": [location.x, location.y, location.z],
                    "scale": [scale.x, scale.y, scale.z]})
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET):
    raise RuntimeError("Could not save candidate pilot map")
out = {"map": TARGET, "source_map": SOURCE, "candidate_pilots": records,
       "other_lots_unchanged": 18 - len(records),
       "note": "Open in graphical editor and generate PCG before visual signoff"}
(ROOT / ("Pipeline/Unreal/reuse_lots_all_map.json" if ALL_LOTS
         else "Pipeline/Unreal/reuse_lots_pilot_map.json")).write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print("M80_REUSE_LOTS_QA", TARGET, len(records))
