"""Record PCG output and component state in the open preview level."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
source = json.loads((root / "Pipeline/Unreal/sample_pcg_actor_inventory.json").read_text(encoding="utf-8"))
out = root / "Pipeline/Unreal/pcg_district_editor_diagnosis.json"
actors = {a.get_actor_label().rsplit("_", 1)[-1]: a for a in
          unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
          if a.get_actor_label().startswith("BP_ProceduralBuilding_")}
rows = {}
def property_or_none(object_, name):
    if not object_:
        return None
    try:
        return object_.get_editor_property(name)
    except Exception:
        return None

for lot, actor in sorted(actors.items()):
    component = actor.get_component_by_class(unreal.PCGComponent)
    meshes = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    graph_instance = component.get_editor_property("graph_instance") if component else None
    graph = graph_instance.get_editor_property("graph") if graph_instance else None
    rows[lot] = {
        "expected": source[lot]["instances"],
        "actual": sum(c.get_instance_count() for c in meshes),
        "instanced_components": len(meshes),
        "generated": bool(component.get_editor_property("generated")) if component else False,
        "generating": property_or_none(component, "generating"),
        "partitioned": bool(component.get_editor_property("is_component_partitioned")) if component else None,
        "graph": graph.get_path_name() if graph else None,
        "location": [actor.get_actor_location().x, actor.get_actor_location().y,
                     actor.get_actor_location().z],
    }
report = {"world": unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name(),
          "houses": rows}
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_PCG_DIAGNOSE", out)
