"""Replace QA-only stage actors with PCG volumes in a duplicated QA map."""
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_QA"
TARGET = "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_PCG_QA"
PILOTS = (("STYLE_01", "1249069204"), ("STYLE_02", "1249068307"),
          ("STYLE_03", "1249069200"), ("STYLE_04", "1249069228"))
if not unreal.EditorAssetLibrary.does_asset_exist(TARGET):
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET):
        raise RuntimeError("Could not duplicate QA map")
world = unreal.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:
    raise RuntimeError("Could not load " + TARGET)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
removed = 0
for actor in actors.get_all_level_actors():
    label = actor.get_actor_label()
    if label.startswith("QA STYLE_") or label.startswith("PCG QA STYLE_"):
        actors.destroy_actor(actor)
        removed += 1

records = []
for index, (style, lot) in enumerate(PILOTS):
    graph_path = "/Game/Mazzarino80/ReuseKit/PCG/PCG_ReuseKit_" + lot
    graph = unreal.EditorAssetLibrary.load_asset(graph_path)
    if not isinstance(graph, unreal.PCGGraph):
        raise RuntimeError("Missing PCG graph: " + graph_path)
    center = unreal.Vector(index * 950, 0, 300)
    volume = actors.spawn_actor_from_class(unreal.PCGVolume, center, unreal.Rotator())
    volume.set_actor_label("PCG QA " + style + " " + lot)
    volume.set_actor_scale3d(unreal.Vector(1.5, 1.5, 1.5))
    component = volume.get_component_by_class(unreal.PCGComponent)
    if component is None:
        raise RuntimeError("PCG volume has no component")
    component.set_graph(graph)
    component.generate(True)
    records.append({"style": style, "lot": lot, "graph": graph_path,
                    "center_cm": [center.x, center.y, center.z]})
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET):
    raise RuntimeError("Could not save PCG QA map")
out = {"map": TARGET, "pilot_volumes": records, "stage_actors_removed": removed,
       "note": "QA-only PCG assemblies; town's irregular 18-lot geometry untouched"}
(ROOT / "Pipeline/Unreal/reuse_pcg_qa_level.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print("M80_REUSE_PCG_QA", TARGET, len(records), "volumes")
