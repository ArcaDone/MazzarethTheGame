"""Test whether blueprint construction creates the missing house geometry."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
out = root / "Pipeline/Unreal/test_preview_construction_refresh.json"
lot = "1249069204"
actor = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
             if a.get_actor_label() == "BP_ProceduralBuilding_" + lot)

def snapshot():
    pcg = actor.get_component_by_class(unreal.PCGComponent)
    gi = pcg.get_editor_property("graph_instance") if pcg else None
    graph = gi.get_editor_property("graph") if gi else None
    meshes = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    return {"instances": sum(m.get_instance_count() for m in meshes),
            "instanced_components": len(meshes),
            "generated": bool(pcg.get_editor_property("generated")) if pcg else None,
            "graph": graph.get_path_name() if graph else None,
            "mesh_summary": [{"name": m.get_name(), "instances": m.get_instance_count()}
                             for m in meshes]}

report = {"lot": lot, "before": snapshot()}
try:
    actor.rerun_construction_scripts()
    report["after_construction"] = snapshot()
    component = actor.get_component_by_class(unreal.PCGComponent)
    if component:
        component.generate(True)
    report["after_generate_call"] = snapshot()
except Exception as exc:
    report["error"] = str(exc)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_PCG_CONSTRUCTION_TEST", out)
