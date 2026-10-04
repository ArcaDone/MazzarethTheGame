import unreal,json
from pathlib import Path
root=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
roads=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline)]
slab=unreal.load_asset('/Game/Mazzarino80/Roads/M80_RoadSlab')
for road in roads:
    if 'Corso Vittorio Emanuele' in road.road_name:road.set_editor_property('road_backing_mesh',slab)
    road.rebuild_road()
def signature():
    roads=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline)]
    result={}
    for a in roads:
        s=a.get_component_by_class(unreal.SplineComponent)
        p=s.get_location_at_spline_point(0,unreal.SplineCoordinateSpace.WORLD)
        result[a.get_actor_label()]={'points':s.get_number_of_spline_points(),'first':[p.x,p.y,p.z],'width':a.width_meters,'segments':a.get_road_segment_count(),'mesh':a.road_mesh.get_path_name(),'backing':a.road_backing_mesh.get_path_name() if a.road_backing_mesh else None}
    return result
before=signature()
assert levels.save_current_level()
assert levels.load_level('/Game/Levels/Main')
assert levels.load_level('/Game/Levels/Mazzarino80_Panoramica')
after=signature()
assert before==after,'Saved spline data changed on reopening'
root.joinpath('Saved/Mazzarino80/roads_persistence.json').write_text(json.dumps({'roads':len(after),'matched_after_reopening':True,'segments':sum(x['segments'] for x in after.values())},indent=2))
corso=next(a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline) and a.get_actor_label().endswith('_1249463304'))
editor.set_selected_level_actors([corso])
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(74500,-10000,20200),unreal.Rotator(pitch=-55,yaw=60,roll=0))
unreal.log('M80_PERSISTENCE_VERIFIED '+str(len(after)))
