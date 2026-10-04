"""Check the exact PCG instances of the two new rooftop tanks."""
import json
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir())
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
report={}
for lot in ('1249069213','1249069271'):
    actor=next(a for a in actors if a.get_actor_label()=='BP_ProceduralBuilding_'+lot)
    found=[]
    for component in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
        mesh=component.get_editor_property('static_mesh')
        if mesh and 'SM_Platform_Water_Tank_01' in mesh.get_path_name():
            found.append({'count':component.get_instance_count(),
                          'locations':[[t.translation.x,t.translation.y,t.translation.z]
                                       for t in [component.get_instance_transform(i,world_space=True)
                                                 for i in range(component.get_instance_count())]]})
    report[lot]=found
(ROOT/'Saved/Mazzarino80/PCG/audit_tank_instances.json').write_text(
    json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_TANK_INSTANCES '+str(report))
