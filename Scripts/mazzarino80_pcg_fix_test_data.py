"""Register the mesh metadata attribute, then regenerate the validation cube."""
import json
import traceback
from pathlib import Path
import unreal

log = {}
try:
    asset = unreal.load_asset("/Game/Mazzarino80/PCG/Validation/PCGDA_TestStructure")
    data = asset.get_editor_property("data").tagged_data[0].data
    metadata = data.mutable_metadata()
    log["before"] = metadata.has_attribute("Mesh")
    if not metadata.has_attribute("Mesh"):
        metadata.create_soft_object_path_attribute("Mesh", unreal.SoftObjectPath(), False)
    point = data.get_point(0)
    point.set_soft_object_path_attribute(metadata, "Mesh", unreal.SoftObjectPath("/Engine/BasicShapes/Cube.Cube"))
    data.set_points([point])
    log["after"] = metadata.has_attribute("Mesh")
    log["saved_asset"] = unreal.EditorAssetLibrary.save_loaded_asset(asset)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    volume = next(a for a in actors if a.get_actor_label() == "M80_PCG_Validation_Cube")
    volume.get_component_by_class(unreal.PCGComponent).generate(True)
except Exception:
    log["error"] = traceback.format_exc()
out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_fix_test_data.json"
out.write_text(json.dumps(log, indent=2), encoding="utf-8")
unreal.log("M80_PCG_FIX_DATA " + str(out))
