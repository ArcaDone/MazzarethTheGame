"""Read PCG runtime state without changing the open level."""
import json
from pathlib import Path
import unreal

actor = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
             if a.get_actor_label().startswith('BP_ProceduralBuilding_'))
pcg = actor.get_component_by_class(unreal.PCGComponent)
box = actor.get_component_by_class(unreal.BoxComponent)
report = {
    'actor': actor.get_actor_label(),
    'pcg_methods': [x for x in dir(pcg) if any(k in x.lower() for k in ('generat', 'partition', 'bound', 'grid', 'clean'))],
    'box': str(box),
    'box_extent': str(box.get_scaled_box_extent()) if box else None,
    'box_tags': [str(t) for t in box.component_tags] if box else [],
    'partitioned': str(pcg.is_component_partitioned),
    'pcg_fields': {},
    'instances': sum(c.get_instance_count() for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent)),
}
for name in ('is_generating', 'generated', 'dirty_generated', 'is_partitioned', 'generation_trigger', 'input_type', 'graph_instance'):
    try:
        report['pcg_fields'][name] = str(pcg.get_editor_property(name))
    except Exception as e:
        report['pcg_fields'][name] = str(e)
Path(unreal.Paths.project_dir(), 'Saved/Mazzarino80/PCG/inspect_component.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
