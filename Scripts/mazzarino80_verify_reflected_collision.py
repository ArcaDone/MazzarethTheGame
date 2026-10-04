import unreal,json
from pathlib import Path
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=editor.get_all_level_actors()
roads=[a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline)]
ignored=[a for a in actors if a.get_actor_label()=='M80_Edifici']
failures=[]
for a in roads:
    s=a.get_component_by_class(unreal.SplineComponent)
    p=s.get_location_at_distance_along_spline(s.get_spline_length()/2,unreal.SplineCoordinateSpace.WORLD)
    hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(p.x,p.y,p.z+300),unreal.Vector(p.x,p.y,p.z-500),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,unreal.DrawDebugTrace.NONE,True)
    values=hit.to_tuple() if hit else ()
    target=values[9] if values and values[0] else None
    if not isinstance(target,unreal.MazzarinoRoadSpline):failures.append(a.get_actor_label())
result={'roads_sampled':len(roads),'road_surface_hits':len(roads)-len(failures),'failures':failures,'buildings_excluded':True}
Path(r'D:\UE5Projects\GameAnimationSample\Saved\Mazzarino80\y_reflection_collision.json').write_text(json.dumps(result,indent=2))
assert not failures,failures[:10]
unreal.log('M80_REFLECTED_COLLISION_VERIFIED '+str(result))
