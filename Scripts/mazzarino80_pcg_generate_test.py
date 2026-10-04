"""Run and inspect the isolated PCG graph after the level is loaded."""
import json
import traceback
from pathlib import Path
import unreal

log = {}
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    volume = next(a for a in actors if a.get_actor_label() == "M80_PCG_Validation_Cube")
    pcg = volume.get_component_by_class(unreal.PCGComponent)
    log["graph"] = str(pcg.get_editor_property("graph_instance"))
    pcg.generate(True)
    log["generated"] = str(pcg.get_editor_property("generated"))
    log["components"] = [str(c) for c in volume.get_components_by_class(unreal.InstancedStaticMeshComponent)]
    log["saved"] = unreal.EditorLevelLibrary.save_current_level()
except Exception:
    log["error"] = traceback.format_exc()
out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_generate_test.json"
out.write_text(json.dumps(log, indent=2), encoding="utf-8")
unreal.log("M80_PCG_GENERATE_TEST " + str(out))
