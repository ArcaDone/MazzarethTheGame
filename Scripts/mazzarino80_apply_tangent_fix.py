"""Regenerate roads with stable end directions, without changing their splines."""
import unreal,json,hashlib
from pathlib import Path
root=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ue.get_editor_world().get_name()=='Main':
    assert levels.load_level('/Game/Levels/Mazzarino80_Panoramica')
assert ue.get_editor_world().get_name()=='Mazzarino80_Panoramica'
camera=ue.get_level_viewport_camera_info()
def roads():
    return [a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline)]
def signature():
    result={}
    for a in roads():
        s=a.get_component_by_class(unreal.SplineComponent)
        points=[]
        for i in range(s.get_number_of_spline_points()):
            p=s.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.LOCAL)
            scale=s.get_scale_at_spline_point(i)
            tangent=s.get_tangent_at_spline_point(i,unreal.SplineCoordinateSpace.LOCAL)
            points.append([list(p.to_tuple()),list(scale.to_tuple()),list(tangent.to_tuple()),str(s.get_spline_point_type(i))])
        result[a.get_actor_label()]={'points':points,'width':a.width_meters,'mesh':a.road_mesh.get_path_name(),'material':a.road_material.get_path_name() if a.road_material else None,'backing':a.road_backing_mesh.get_path_name() if a.road_backing_mesh else None,'closed':s.is_closed_loop()}
    return result
def audit():
    total=zero=0
    for a in roads():
        for c in a.get_components_by_class(unreal.SplineMeshComponent):
            total+=1
            zero+=int(c.get_start_tangent().length()<0.01)+int(c.get_end_tangent().length()<0.01)
    return {'segments':total,'zero_end_directions':zero}
before=signature()
old=audit()
for a in roads():a.rebuild_road()
assert signature()==before,'Regeneration changed a road spline'
fixed=audit()
assert fixed['zero_end_directions']==0,fixed
assert levels.save_current_level()
assert levels.load_level('/Game/Levels/Main')
assert levels.load_level('/Game/Levels/Mazzarino80_Panoramica')
assert signature()==before,'Reopening changed a road spline'
persisted=audit()
assert persisted==fixed,(persisted,fixed)
result={'roads':len(before),'points':sum(len(v['points']) for v in before.values()),'before':old,'after':fixed,'all_spline_data_preserved':True,'saved_and_reopened':True,'spline_data_sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()}
root.joinpath('Saved/Mazzarino80/tangent_fix_validation.json').write_text(json.dumps(result,indent=2))
road=next(a for a in roads() if a.get_actor_label().endswith('_1249817820'))
editor.set_selected_level_actors([road])
ue.set_level_viewport_camera_info(camera[0],camera[1])
unreal.log('M80_TANGENT_FIX_VERIFIED '+str(result))
