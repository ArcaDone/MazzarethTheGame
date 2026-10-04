"""Read-only source transforms and graph bindings for city preview transfer."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
world = unreal.EditorLoadingAndSavingUtils.load_map(
    "/Game/Levels/Mazzarino80_CaseStoriche_Campione")
if not world:
    raise RuntimeError("Could not load source sample")
rows = {}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    label = actor.get_actor_label()
    if not label.startswith("BP_ProceduralBuilding_"):
        continue
    lot = label.rsplit("_", 1)[-1]
    t = actor.get_actor_transform()
    pcg = actor.get_component_by_class(unreal.PCGComponent)
    gi = pcg.get_editor_property("graph_instance") if pcg else None
    graph = gi.get_editor_property("graph") if gi else None
    data = actor.get_editor_property("building_data")
    rows[lot] = {"label": label,
                 "location_cm": list(t.translation.to_tuple()),
                 "rotation_quat": list(t.rotation.to_tuple()),
                 "scale": list(t.scale3d.to_tuple()),
                 "graph": graph.get_path_name() if graph else None,
                 "building_data_id": data.get_editor_property("building_id") if data else None,
                 "generated": bool(pcg.get_editor_property("generated")) if pcg else False,
                 "instances": sum(c.get_instance_count() for c in
                                  actor.get_components_by_class(unreal.InstancedStaticMeshComponent))}
out = root / "Pipeline/Unreal/sample_pcg_actor_inventory.json"
out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print("M80_SAMPLE_PCG_AUDIT", len(rows), sum(x["instances"] for x in rows.values()))
