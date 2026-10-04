"""Verify all PCG modules against approved source transforms and stage totals."""
import json
from collections import Counter
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
source=json.loads((root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))['houses']
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
report={'houses':{},'expected':0,'actual':0,'missing':0,'extra':0,'errors':[]}
def key(mesh,p):
    return (mesh,round(p[0],1),round(p[1],1),round(p[2],1))
for lot,house in source.items():
    actor=actors.get('BP_ProceduralBuilding_'+lot)
    if not actor:
        report['errors'].append(lot+': missing actor')
        continue
    expected=Counter(key(p['mesh'],p['location_cm']) for points in house['stage_points'].values() for p in points)
    actual=Counter()
    components=actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    for comp in components:
        mesh=comp.get_editor_property('static_mesh')
        name=mesh.get_path_name() if mesh else ''
        for i in range(comp.get_instance_count()):
            v=comp.get_instance_transform(i,world_space=True).translation
            actual[key(name,(v.x,v.y,v.z))]+=1
    missing=sum((expected-actual).values())
    extra=sum((actual-expected).values())
    pcg=actor.get_component_by_class(unreal.PCGComponent)
    item={'expected':sum(expected.values()),'actual':sum(actual.values()),'missing':missing,'extra':extra,
          'ism_components':len(components),'generated':pcg.generated,'partitioned':pcg.is_component_partitioned,
          'stages':{stage:len(points) for stage,points in house['stage_points'].items()}}
    report['houses'][lot]=item
    report['expected']+=item['expected']
    report['actual']+=item['actual']
    report['missing']+=missing
    report['extra']+=extra
    if missing or extra or not pcg.generated or pcg.is_component_partitioned:
        report['errors'].append(lot+': '+str(item))
(root/'Saved/Mazzarino80/PCG/verify_approved_all.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_PCG_APPROVED_VERIFY '+str(report['actual'])+'/'+str(report['expected'])+', errors '+str(len(report['errors'])))
