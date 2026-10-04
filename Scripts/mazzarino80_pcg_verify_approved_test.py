"""Check that the PCG instances match approved modules in world space."""
import json
from collections import Counter
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
lot='1249069275'
house=json.loads((root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))['houses'][lot]
actor=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
           if a.get_actor_label()=='BP_ProceduralBuilding_'+lot)
def key(mesh,pos):
    return (mesh,round(pos[0],1),round(pos[1],1),round(pos[2],1))
expected=Counter(key(p['mesh'],p['location_cm']) for points in house['stage_points'].values() for p in points)
actual=Counter()
components=[]
for comp in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
    mesh=comp.get_editor_property('static_mesh')
    name=mesh.get_path_name() if mesh else ''
    count=comp.get_instance_count()
    components.append({'mesh':name,'count':count})
    for i in range(count):
        v=comp.get_instance_transform(i,world_space=True).translation
        actual[key(name,(v.x,v.y,v.z))]+=1
missing=expected-actual
extra=actual-expected
report={'expected':sum(expected.values()),'actual':sum(actual.values()),
        'missing':sum(missing.values()),'extra':sum(extra.values()),
        'missing_sample':list(missing.items())[:12],'extra_sample':list(extra.items())[:12],
        'components':components}
(root/'Saved/Mazzarino80/PCG/verify_approved_test.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
