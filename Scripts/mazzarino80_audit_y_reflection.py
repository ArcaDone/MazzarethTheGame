import unreal,json
from pathlib import Path
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rows=[]
roads=[]
for a in editor.get_all_level_actors():
    p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
    row={'label':a.get_actor_label(),'class':a.get_class().get_name(),'location':list(p.to_tuple()),'rotation':[r.pitch,r.yaw,r.roll],'scale':list(s.to_tuple()),'parent':a.get_attach_parent_actor().get_actor_label() if a.get_attach_parent_actor() else None}
    if isinstance(a,unreal.MazzarinoRoadSpline):roads.append(row)
    else:
        component=a.get_component_by_class(unreal.StaticMeshComponent)
        if component and component.static_mesh:row['mesh']=component.static_mesh.get_path_name()
        rows.append(row)
meshes={}
for path in ['/Game/Mazzarino80/Overview/M80_Terreno1','/Game/Mazzarino80/Overview/M80_Edifici_Mesh','/Game/Mazzarino80/Roads/CorrectedBase/M80_Terreno_Corrected','/Game/Mazzarino80/Roads/CorrectedBase/M80_Edifici_Corrected']:
    m=unreal.load_asset(path)
    b=m.get_bounding_box()
    meshes[path]={'min':list(b.min.to_tuple()),'max':list(b.max.to_tuple())}
result={'actors':rows,'roads':len(roads),'unusual_roads':[x for x in roads if x['rotation']!=[0,0,0] or x['scale']!=[1,1,1] or x['parent']], 'mesh_bounds':meshes}
Path(r'D:\UE5Projects\GameAnimationSample\Saved\Mazzarino80\y_reflection_audit.json').write_text(json.dumps(result,indent=2))
unreal.log('M80_Y_REFLECTION_AUDIT')
