import unreal,json
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level('/Game/Levels/Mazzarino80_Base')
descs=unreal.WorldPartitionBlueprintLibrary.get_actor_descs() or []
unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in descs])
names={'ComuneCompleto','A_ZzaRita','A_Liardo','A_Madonna','A_SanDomenico','ScuolaMatrice','CastelCompleted','Matrice','A_Salesiane','A_Agip'}
def v(p):return list(p.to_tuple())
def t(transform):
    r=transform.rotation.rotator()
    return {'translation':v(transform.translation),'rotation':[r.pitch,r.yaw,r.roll],'scale':v(transform.scale3d)}
result=[]
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() not in names:continue
    row={'label':a.get_actor_label(),'class':a.get_class().get_path_name(),'transform':t(a.get_actor_transform()),'components':[]}
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if not c.static_mesh:continue
        center,extent=unreal.SystemLibrary.get_component_bounds(c)[:2]
        row['components'].append({'name':c.get_name(),'mesh':c.static_mesh.get_path_name(),'transform':t(c.get_world_transform()),'center':v(center),'extent':v(extent),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
    result.append(row)
assert len(result)==10,[x['label'] for x in result]
(ROOT/'Research/Mazzarino80/prepared_buildings_inventory.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
unreal.log('M80_PREPARED_BUILDINGS_INVENTORY '+str(len(result)))

