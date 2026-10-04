"""Hide only the 67 replaced building volumes in the Batch01 FullPCG map.

Their footprint actors remain in the map as editable source data.  Refuse to
hide anything until all five PCG stages have generated their expected points.
"""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
map_name = "Mazzarino80_PCG_Quartieri_Batch01_FullPCG"
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not world or world.get_name() != map_name:
    raise RuntimeError("Open the Batch01 FullPCG map first")

generation = json.loads((root / "Pipeline/Unreal/first_pcg_batch_full_editor_generation.json").read_text(encoding="utf-8"))
catalog = json.loads((root / "Research/Mazzarino80/PCG/DistrictBatch01_Full/full_pcg_points.json").read_text(encoding="utf-8"))
expected = {house["building_id"]: sum(len(points) for points in house["stage_points"].values())
            for house in catalog["houses"]}
if generation["status"] != "generated_needs_gui_save" or len(expected) != 67:
    raise RuntimeError("Full generation is not verified")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
pcg = {a.get_actor_label().removeprefix("PCG_Building_"): a for a in actors
       if a.get_actor_label().startswith("PCG_Building_")}
sources = {str(a.get_editor_property("building_id")): a for a in actors
           if isinstance(a, unreal.MazzarinoBuilding)}
if set(pcg) != set(expected) or not set(expected) <= set(sources):
    raise RuntimeError("The generated and source actor inventories differ")

counts = {lot: sum(c.get_instance_count() for c in
                   pcg[lot].get_components_by_class(unreal.InstancedStaticMeshComponent))
          for lot in expected}
wrong = {lot: [expected[lot], counts[lot]] for lot in expected if counts[lot] != expected[lot]}
if wrong:
    raise RuntimeError("Refusing to hide incomplete houses: " + str(wrong))

report = {"map": "/Game/Levels/" + map_name,
          "pcg_houses_verified": 67, "generated_instances": sum(counts.values()),
          "hidden_source_volumes": [], "source_footprints_retained": True,
          "all_other_source_volumes_untouched": True}
for lot in sorted(expected):
    actor = sources[lot]
    actor.set_actor_hidden_in_game(True)
    actor.set_actor_enable_collision(False)
    actor.set_is_temporarily_hidden_in_editor(True)
    actor.set_folder_path("Mazzarino80/Quartieri_PCG/Perimetri_originali_nascosti")
    components = actor.get_components_by_class(unreal.PrimitiveComponent)
    for component in components:
        component.set_visibility(False)
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    report["hidden_source_volumes"].append({"lot": lot, "components": len(components)})

out = root / "Pipeline/Unreal/first_pcg_batch_full_hide_result.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_FULL_PLACEHOLDERS_HIDDEN", len(report["hidden_source_volumes"]))
