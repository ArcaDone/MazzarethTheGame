import unreal,json
from pathlib import Path
root=Path(r'D:\UE5Projects\GameAnimationSample')
e=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
camera=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_level_viewport_camera_info()
out={'camera':[list(v.to_tuple()) for v in camera], 'landmarks':[],'materials':[]}
for a in e.get_all_level_actors():
    if a.get_actor_label().startswith('M80_Recuperato_'):
        c,x=a.get_actor_bounds(False)
        out['landmarks'].append({'label':a.get_actor_label(),'location':list(a.get_actor_location().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple()),'center':list(c.to_tuple()),'extent':list(x.to_tuple())})
    if isinstance(a,unreal.MazzarinoBuilding) and a.get_editor_property('detailed_facade'):
        m=a.get_editor_property('facade_material')
        out['materials'].append({'id':a.get_editor_property('building_id'),'material':m.get_path_name() if m else None})
(root/'Saved/Mazzarino80/current_view_audit.json').write_text(json.dumps(out,indent=2))
assert unreal.EditorLevelLibrary.save_current_level()
unreal.log('M80_VIEW_AUDIT_SAVED')
