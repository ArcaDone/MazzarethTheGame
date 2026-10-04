"""Verify the temporary nineteenth PCG house after the editor has ticked."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
actor=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
           if a.get_actor_label()=='BP_ProceduralBuilding_19_TEST')
pcg=actor.get_component_by_class(unreal.PCGComponent)
counts={}
for component in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
    mesh=component.get_editor_property('static_mesh')
    name=mesh.get_path_name() if mesh else ''
    counts[name]=counts.get(name,0)+component.get_instance_count()
expected=json.loads((root/'Saved/Mazzarino80/PCG/house19_begin.json').read_text(encoding='utf-8'))['expected_points']
report={'actor':actor.get_actor_label(),'expected':expected,'actual':sum(counts.values()),
        'mesh_count':len(counts),'generated':pcg.generated,
        'partitioned':pcg.is_component_partitioned,'uses_approved_modules':
        any('/ApprovedModules/' in key for key in counts),
        'passed':sum(counts.values())==expected and pcg.generated and not pcg.is_component_partitioned}
(root/'Saved/Mazzarino80/PCG/house19_verify.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
