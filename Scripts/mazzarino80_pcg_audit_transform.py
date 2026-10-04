import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
lot='1249069275'
source=json.loads((root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))['houses'][lot]
actor=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
           if a.get_actor_label()=='BP_ProceduralBuilding_'+lot)
sample=source['stage_points']['Structure'][0]
rows=[]
for comp in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
    mesh=comp.get_editor_property('static_mesh')
    if mesh and mesh.get_path_name()==sample['mesh']:
        rows.append({'name':comp.get_name(),'transform':str(comp.get_instance_transform(0,world_space=True)),
                     'relative':str(comp.get_instance_transform(0,world_space=False))})
(root/'Saved/Mazzarino80/PCG/audit_transform.json').write_text(json.dumps({'source':sample,'actor_scale':str(actor.get_actor_scale3d()),'generated':rows},indent=2),encoding='utf-8')
