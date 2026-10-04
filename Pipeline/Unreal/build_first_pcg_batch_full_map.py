"""Stage full PCG replacements in a separate level without hiding originals yet.

The placeholder building surfaces are hidden only after the PCG generation is
validated in the ticking graphical editor.
"""
from hashlib import sha256
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
manifest = json.loads((root / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
source = "/Game/Levels/Mazzarino80_PCG_Quartieri_Batch01"
target = "/Game/Levels/Mazzarino80_PCG_Quartieri_Batch01_FullPCG"
out = root / "Pipeline/Unreal/first_pcg_batch_full_map_result.json"
protected = {name: root / ("Content/Levels/" + name + ".umap") for name in
             ("Mazzarino80_Panoramica", "Mazzarino80_CaseStoriche_Campione",
              "Mazzarino80_PCG_Quartieri_Preview", "Mazzarino80_PCG_Quartieri_Batch01")}
before = {name: sha256(path.read_bytes()).hexdigest() for name, path in protected.items()}
if unreal.EditorAssetLibrary.does_asset_exist(target):
    raise RuntimeError("FullPCG map exists; refusing to overwrite")
if not unreal.EditorAssetLibrary.duplicate_asset(source, target):
    raise RuntimeError("Could not duplicate first-batch map")
world = unreal.EditorLoadingAndSavingUtils.load_map(target)
if not world or world.get_name() != "Mazzarino80_PCG_Quartieri_Batch01_FullPCG":
    raise RuntimeError("Wrong FullPCG map loaded")
all_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
volumes = {a.get_actor_label().removeprefix("PCG_Detail_"): a for a in all_actors
           if a.get_actor_label().startswith("PCG_Detail_")}
sources = {str(a.get_editor_property("building_id")): a for a in all_actors
           if isinstance(a, unreal.MazzarinoBuilding)}
expected = set().union(*(set(d["lots"]) - set(d["approved_pcg_lots"])
                         for d in manifest["districts"][:3]))
if len(expected) != 67 or set(volumes) != expected or not expected <= set(sources):
    raise RuntimeError("Unexpected volume or perimeter inventory")
report = {"map": target, "source": source, "rebound": {},
          "placeholder_walls_hidden": False, "errors": []}
for district in manifest["districts"][:3]:
    for lot in district["lots"]:
        if lot not in expected:
            continue
        actor = volumes[lot]
        graph_path = "/Game/Mazzarino80/PCG/DistrictBatch01_Full/PCG_Building_" + lot
        graph = unreal.load_asset(graph_path)
        if not isinstance(graph, unreal.PCGGraph):
            report["errors"].append("Missing full PCG graph " + lot)
            continue
        component = actor.get_component_by_class(unreal.PCGComponent)
        if not component:
            report["errors"].append("No PCG component " + lot)
            continue
        component.cleanup(True)
        component.set_graph(graph)
        actor.set_actor_label("PCG_Building_" + lot)
        actor.set_folder_path("Mazzarino80/Quartieri_PCG/" + district["id"] + "/Case_PCG")
        report["rebound"][lot] = {"district": district["id"],
                                   "graph": graph_path,
                                   "actor": actor.get_actor_label()}
if len(report["rebound"]) != 67 or report["errors"]:
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    raise RuntimeError("Could not bind all 67 full PCG graphs")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, target):
    raise RuntimeError("FullPCG map could not be saved")
after = {name: sha256(path.read_bytes()).hexdigest() for name, path in protected.items()}
report["source_maps_unchanged"] = before == after
report["saved"] = True
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
if before != after:
    raise RuntimeError("A protected map changed")
print("M80_FIRST_BATCH_FULL_MAP", len(report["rebound"]))
