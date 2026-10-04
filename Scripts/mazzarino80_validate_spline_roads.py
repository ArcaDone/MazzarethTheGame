"""Check geometry regeneration, saved point data, and representative surface collision."""
import json,math
from pathlib import Path
import unreal
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name()=='Mazzarino80_Panoramica'
actors=editor.get_all_level_actors()
roads=[a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline)]
assert len(roads)==1016
corso=next(a for a in roads if a.get_actor_label().endswith('_1249463304'))
spline=corso.get_component_by_class(unreal.SplineComponent)
coord=unreal.SplineCoordinateSpace.LOCAL
index=10
old_position=spline.get_location_at_spline_point(index,coord)
old_scale=spline.get_scale_at_spline_point(index)
old_width=corso.width_meters
new_position=unreal.Vector(old_position.x,old_position.y,old_position.z+50)
spline.set_location_at_spline_point(index,new_position,coord,False)
spline.set_scale_at_spline_point(index,unreal.Vector(1,1.25,1),True)
corso.set_editor_property('width_meters',old_width+1)
corso.rebuild_road()
target_distance=spline.get_distance_along_spline_at_spline_point(index)
mesh_width=corso.road_mesh.get_bounding_box().max.y-corso.road_mesh.get_bounding_box().min.y
expected_scale=(old_width+1)*100/mesh_width*1.25
segments=[s for s in corso.get_components_by_class(unreal.SplineMeshComponent) if s.static_mesh==corso.road_mesh]
closest=min(segments,key=lambda s:(s.get_start_position()-new_position).length())
scale_error=abs(closest.get_start_scale().x-expected_scale)
position_error=(closest.get_start_position()-new_position).length()
assert scale_error<0.0001 and position_error<0.1,(scale_error,position_error)
functional={'height_change_cm':50,'point_width_multiplier':1.25,'road_width_change_m':1,'segment_position_error_cm':position_error,'segment_scale_error':scale_error}
spline.set_location_at_spline_point(index,old_position,coord,False)
spline.set_scale_at_spline_point(index,old_scale,True)
corso.set_editor_property('width_meters',old_width)
corso.rebuild_road()

ignored=[a for a in actors if a.get_actor_label()=='M80_Edifici']
def trace(actor,distance):
    component=actor.get_component_by_class(unreal.SplineComponent)
    p=component.get_location_at_distance_along_spline(distance,unreal.SplineCoordinateSpace.WORLD)
    hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(p.x,p.y,p.z+300),unreal.Vector(p.x,p.y,p.z-500),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,unreal.DrawDebugTrace.NONE,True)
    values=hit.to_tuple() if hit else ()
    target=values[9] if values and values[0] else None
    return {'road':actor.get_actor_label(),'distance_cm':distance,'hit':target.get_actor_label() if target else None,'road_hit':isinstance(target,unreal.MazzarinoRoadSpline),'z_cm':values[4].z if target else None}
samples=[trace(a,a.get_component_by_class(unreal.SplineComponent).get_spline_length()*0.5) for a in roads]
corso_samples=[]
for a in roads:
    if 'Corso Vittorio Emanuele' not in a.road_name:continue
    length=a.get_component_by_class(unreal.SplineComponent).get_spline_length()
    count=max(2,math.ceil(length/500))
    corso_samples.extend(trace(a,length*(i+0.5)/count) for i in range(count))
for path in ['/Game/Mazzarino80/Overview/M80_Strade','/Game/Mazzarino80/RoadSource/Migrated/Materials/Material']:
    unreal.EditorAssetLibrary.save_asset(path,only_if_is_dirty=True)
assert levels.save_current_level()
slab=unreal.load_asset('/Game/Mazzarino80/Roads/M80_RoadSlab')
components=corso.get_components_by_class(unreal.SplineMeshComponent)
result={'roads':len(roads),'lava_nanite':str(corso.road_mesh.get_editor_property('nanite_settings')),'first_lava_component':{'location':str(components[0].get_world_location()),'bounds':str(components[0].get_local_bounds()),'visible':components[0].is_visible(),'start_scale':str(components[0].get_start_scale()),'start_offset':str(components[0].get_start_offset()),'up_dir':str(components[0].get_spline_up_dir())},'slab_bounds':str(slab.get_bounding_box()),'functional':functional,'midpoint_road_hits':sum(x['road_hit'] for x in samples),'midpoint_samples':samples,'corso_road_hits':sum(x['road_hit'] for x in corso_samples),'corso_samples':corso_samples,'buildings_ignored_for_surface_audit':True}
(ROOT/'Saved/Mazzarino80/roads_validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
editor.set_selected_level_actors([corso])
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(72700,-10500,18400),unreal.Rotator(pitch=-25,yaw=35,roll=0))
unreal.log('M80_ROAD_VALIDATE_DONE '+str(result['midpoint_road_hits'])+'/'+str(len(samples))+' Corso '+str(result['corso_road_hits'])+'/'+str(len(corso_samples)))
