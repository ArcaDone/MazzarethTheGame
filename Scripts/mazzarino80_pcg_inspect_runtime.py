"""Inspect generated PCG components after editor tick."""
import json
import traceback
from pathlib import Path
import unreal

log = {}
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for actor in actors:
        comps = []
        for component in actor.get_components_by_class(unreal.ActorComponent):
            if isinstance(component, unreal.InstancedStaticMeshComponent):
                comps.append({"name": str(component), "instance_count": component.get_instance_count(), "mesh": str(component.get_editor_property("static_mesh"))})
        log[actor.get_actor_label()] = {"class": str(actor.get_class()), "ism": comps}
        pcg = actor.get_component_by_class(unreal.PCGComponent)
        if pcg:
            log[actor.get_actor_label()]["generated"] = str(pcg.get_editor_property("generated"))
            log[actor.get_actor_label()]["pcg_fields"] = [x for x in dir(pcg) if "generat" in x or "resource" in x]
    house = next((a for a in actors if a.get_actor_label() == "BP_ProceduralBuilding_1249069247"), None)
    if house:
        center = house.get_actor_location()
        camera = unreal.Vector(center.x - 1900, center.y - 2000, center.z + 950)
        rotation = unreal.MathLibrary.find_look_at_rotation(camera, center)
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera, rotation)
except Exception:
    log["error"] = traceback.format_exc()
out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_runtime_inspection.json"
out.write_text(json.dumps(log, indent=2), encoding="utf-8")
unreal.log("M80_PCG_RUNTIME_INSPECT " + str(out))
