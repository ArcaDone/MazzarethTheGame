"""Compare intended module coordinates with spawned world transforms."""
import json
import traceback
from pathlib import Path
import unreal

log = {}
try:
    actor = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() == "BP_ProceduralBuilding_1249069247")
    log["actor_transform"] = str(actor.get_actor_transform())
    for comp in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
        rows = []
        for idx in range(min(3, comp.get_instance_count())):
            rows.append(str(comp.get_instance_transform(idx, world_space=True)))
        log[comp.get_name()] = {"count": comp.get_instance_count(), "material": str(comp.get_material(0)), "transforms": rows}
    specs = json.loads((Path(unreal.Paths.project_dir()) / "Research/Mazzarino80/PCG/Buildings_Test18_PCGPoints.json").read_text(encoding="utf-8"))
    house = next(x for x in specs["houses"] if x["building_id"] == "1249069247")
    log["intended_structure"] = house["stage_points"]["Structure"][:3]
    log["intended_roof"] = house["stage_points"]["Roofs"][:3]
except Exception:
    log["error"] = traceback.format_exc()
out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_transform_inspection.json"
out.write_text(json.dumps(log, indent=2), encoding="utf-8")
unreal.log("M80_PCG_TRANSFORM_INSPECT " + str(out))
