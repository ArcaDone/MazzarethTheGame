"""Group every Panoramica house under a Q001-Q108 editor visibility folder."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
manifest = json.loads((root / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
out = root / "Pipeline/Unreal/pcg_district_folder_result.json"
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not world or world.get_name() != "Mazzarino80_PCG_Quartieri_Preview":
    raise RuntimeError("Open the separate district preview first")
buildings = {str(a.get_editor_property("building_id")): a for a in
             unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
             if isinstance(a, unreal.MazzarinoBuilding)}
expected = {lot for district in manifest["districts"] for lot in district["lots"]}
if set(buildings) != expected:
    raise RuntimeError("The preview footprint inventory does not match the district plan")
changes = 0
for district in manifest["districts"]:
    approved = set(district["approved_pcg_lots"])
    for lot in district["lots"]:
        target = ("Mazzarino80/Quartieri_PCG/" + district["id"] + "/" +
                  ("Perimetri_originali" if lot in approved else "Volumi_provvisori"))
        actor = buildings[lot]
        if str(actor.get_folder_path()) != target:
            actor.set_folder_path(target)
            changes += 1
result = {"map": world.get_name(), "districts": len(manifest["districts"]),
          "footprints": len(buildings), "folder_changes": changes,
          "all_footprints_grouped": True, "saved": False}
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_PCG_DISTRICT_FOLDERS", len(buildings), changes)
