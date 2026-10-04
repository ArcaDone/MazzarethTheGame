"""Validate the PCG data-to-mesh path in an isolated editor level."""
import json
import traceback
from pathlib import Path

import unreal

result = {}
try:
    level = "/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_Validation"
    result["current_level_saved"] = unreal.EditorLevelLibrary.save_current_level()
    if not unreal.EditorAssetLibrary.does_asset_exist(level):
        result["new_level"] = unreal.EditorLevelLibrary.new_level(level)
    else:
        result["level_loaded"] = unreal.EditorLevelLibrary.load_level(level)
    graph = unreal.load_asset("/Game/Mazzarino80/PCG/Validation/PCG_TestStructure_V2")
    result["volume_class"] = str(getattr(unreal, "PCGVolume", None))
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    volume = actor_subsystem.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector(0, 0, 0))
    volume.set_actor_label("M80_PCG_Validation_Cube")
    result["volume"] = str(volume)
    result["volume_fields"] = [x for x in dir(volume) if "pcg" in x.lower() or "component" in x.lower()][:80]
    pcg = volume.get_component_by_class(unreal.PCGComponent)
    result["pcg"] = str(pcg)
    pcg.set_graph(graph)
    result["generate_doc"] = str(pcg.generate.__doc__)[:700]
    pcg.generate()
    result["save_validation_level"] = unreal.EditorLevelLibrary.save_current_level()
except Exception:
    result["error"] = traceback.format_exc()

out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_runtime_test.json"
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
unreal.log("M80_PCG_RUNTIME_TEST " + str(out))
