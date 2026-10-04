"""Citywide context with the approved 18 PCG houses grouped in three sectors.

This copies Panoramica. The other 3,198 footprint actors remain the existing
procedural volumes, not PCG conversions.
"""
from hashlib import sha256
from pathlib import Path
import json
import unreal

ROOT = Path(unreal.Paths.project_dir())
MANIFEST = json.loads((ROOT / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
SAMPLE = json.loads((ROOT / "Pipeline/Unreal/sample_pcg_actor_inventory.json").read_text(encoding="utf-8"))
SOURCE = "/Game/Levels/Mazzarino80_Panoramica"
DEST = MANIFEST["preview_map"]
OUT = ROOT / "Pipeline/Unreal/pcg_district_preview_result.json"
source_file = ROOT / "Content/Levels/Mazzarino80_CaseStoriche_Campione.umap"
panorama_file = ROOT / "Content/Levels/Mazzarino80_Panoramica.umap"
before = {"sample": sha256(source_file.read_bytes()).hexdigest(),
          "panorama": sha256(panorama_file.read_bytes()).hexdigest()}
if unreal.EditorAssetLibrary.does_asset_exist(DEST):
    raise RuntimeError("District preview already exists; refuse to overwrite it")
if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, DEST):
    raise RuntimeError("Could not duplicate Panoramica")
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(DEST):
    raise RuntimeError("Could not open the independent district preview")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world.get_name() != "Mazzarino80_PCG_Quartieri_Preview":
    raise RuntimeError("Unexpected map open")
editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = editor.get_all_level_actors()
by_lot = {str(a.get_editor_property("building_id")): a for a in actors
          if isinstance(a, unreal.MazzarinoBuilding)}
if len(by_lot) != MANIFEST["footprint_count"] or set(SAMPLE) - set(by_lot):
    raise RuntimeError("Panoramica footprint inventory differs from the manifest")
catalog = unreal.load_asset("/Game/Mazzarino80/PCG/DA_Buildings_Test18")
blueprint = unreal.EditorAssetLibrary.load_blueprint_class(
    "/Game/Mazzarino80/PCG/BP_ProceduralBuilding")
if not catalog or not blueprint:
    raise RuntimeError("Approved PCG catalog or building blueprint is missing")
records = {str(d.get_editor_property("building_id")): d for d in
           catalog.get_editor_property("buildings")}
changes, errors, created = [], [], []
for sector in MANIFEST["districts"][:3]:
    base = "Mazzarino80/Quartieri_PCG/" + sector["id"]
    pcg_lots = set(sector["approved_pcg_lots"])
    for lot in sector["lots"]:
        source = by_lot[lot]
        source.set_folder_path(base + ("/Perimetri_originali" if lot in pcg_lots
                                       else "/Volumi_provvisori"))
    for lot in sorted(pcg_lots):
        info = SAMPLE[lot]
        graph_path = ("/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1/"
                      "PCG_Building_" + lot)
        graph = unreal.load_asset(graph_path)
        if not graph or lot not in records:
            errors.append("Missing graph/catalog record: " + lot)
            continue
        actor = editor.spawn_actor_from_class(blueprint, unreal.Vector(*info["location_cm"]))
        actor.set_actor_label(info["label"])
        actor.set_actor_scale3d(unreal.Vector(*info["scale"]))
        actor.set_editor_property("building_data", records[lot])
        actor.set_folder_path(base + "/Case_PCG_approvate")
        component = actor.get_component_by_class(unreal.PCGComponent)
        if not component:
            errors.append("Spawned actor lacks PCG component: " + lot)
            continue
        component.set_editor_property("is_component_partitioned", False)
        component.set_graph(graph)
        component.generate(True)
        source = by_lot[lot]
        source.set_actor_hidden_in_game(True)
        source.set_is_temporarily_hidden_in_editor(True)
        source.set_actor_enable_collision(False)
        for primitive in source.get_components_by_class(unreal.PrimitiveComponent):
            primitive.set_visibility(False)
            primitive.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        created.append({"lot": lot, "graph": graph_path,
                        "actor": actor.get_actor_label(),
                        "folder": str(actor.get_folder_path())})
    changes.append({"id": sector["id"], "source_folder": sector["source_folder"],
                    "new_folder": base, "footprints": sector["building_count"],
                    "approved_pcg_lots": sorted(pcg_lots)})
for sector in MANIFEST["districts"][3:]:
    base = "Mazzarino80/Quartieri_PCG/" + sector["id"] + "/Volumi_provvisori"
    for lot in sector["lots"]:
        by_lot[lot].set_folder_path(base)
if len(created) != len(SAMPLE):
    errors.append("Did not spawn all 18 approved PCG actors")
if errors:
    OUT.write_text(json.dumps({"errors": errors, "changes": changes}, indent=2), encoding="utf-8")
    raise RuntimeError("District preview failed validation: " + repr(errors[:3]))
if not levels.save_current_level():
    raise RuntimeError("Could not save the district preview map")
after = {"sample": sha256(source_file.read_bytes()).hexdigest(),
         "panorama": sha256(panorama_file.read_bytes()).hexdigest()}
if before != after:
    raise RuntimeError("A protected source map was modified")
report = {"preview_map": DEST, "first_batch": changes,
          "total_footprints_in_map": len(by_lot), "district_folders": len(MANIFEST["districts"]),
          "approved_pcg_in_map": len(created),
          "created": created, "protected_hashes_before": before,
          "protected_hashes_after": after, "source_maps_unchanged": True,
          "remaining_footprints_converted_to_pcg": False,
          "pcg_generation_may_be_async": True, "errors": []}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_PCG_DISTRICT_PREVIEW", len(changes), len(created), len(by_lot))
