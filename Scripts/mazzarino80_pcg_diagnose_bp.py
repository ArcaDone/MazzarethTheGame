"""Inspect the first migrated procedural building in the open level."""
import json
from pathlib import Path
import unreal

actor = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
             if a.get_actor_label().startswith('BP_ProceduralBuilding_'))
pcg = actor.get_component_by_class(unreal.PCGComponent)
data = actor.get_editor_property('building_data')
before = sum(c.get_instance_count() for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent))
graph = data.get_editor_property('building_graph')
pcg.cleanup(True)
pcg.set_graph(graph)
pcg.generate(True)
report = {
    'actor': str(actor),
    'class': str(actor.get_class()),
    'data_id': data.get_editor_property('building_id'),
    'graph_data': str(data.get_editor_property('building_graph')),
    'pcg': str(pcg),
    'graph_component': str(pcg.get_editor_property('graph_instance')) if pcg else None,
    'actor_location': str(actor.get_actor_location()),
    'actor_scale': str(actor.get_actor_scale3d()),
    'actor_bounds': str(actor.get_actor_bounds(False)),
    'pcg_graph': str(pcg.get_editor_property('graph_instance').get_editor_property('graph')),
    'pcg_activated': str(pcg.get_editor_property('activated')),
    'generated_before': before,
    'generated_after': sum(c.get_instance_count() for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent)),
}
Path(unreal.Paths.project_dir(), 'Saved/Mazzarino80/PCG/diagnose_bp.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
