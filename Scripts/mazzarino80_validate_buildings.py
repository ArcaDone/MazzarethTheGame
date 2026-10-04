import unreal,json,math
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Levels/Mazzarino80_Panoramica')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
buildings=[a for a in actors if isinstance(a,unreal.MazzarinoBuilding)]
plan={r['id']:r for r in json.loads((ROOT/'Research/Mazzarino80/building_footprint_plan.json').read_text())}
max_error=0;errors=[];pilot=[]
for a in buildings:
    id=a.get_editor_property('building_id');p=a.get_editor_property('footprint');row=plan[id]
    assert p.get_number_of_spline_points()==len(row['ring_cm']),id
    for i,q in enumerate(row['ring_cm']):
        actual=p.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD)
        max_error=max(max_error,math.dist(q,[actual.x,actual.y]))
    error=a.get_editor_property('geometry_error')
    if error:errors.append([id,error])
    surface=a.get_editor_property('building_surface')
    if surface.get_num_sections()!=2:errors.append([id,'Missing wall/roof sections'])
    if row['pilot']:
        pilot.append({'id':id,'windows':a.get_editor_property('windows').get_instance_count(),'doors':a.get_editor_property('doors').get_instance_count(),'roof_rise_m':a.get_editor_property('roof_rise_meters'),'material':a.get_editor_property('facade_material').get_path_name()})
roads=[a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline)]
assert len(buildings)==3216 and len(roads)==1016,(len(buildings),len(roads))
assert not errors and max_error<.01,(errors,max_error)
assert len(pilot)==14 and all(r['doors']==1 for r in pilot),pilot
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
hits=[]
for a in buildings:
    if not plan[a.get_editor_property('building_id')]['pilot']:continue
    p=a.get_editor_property('footprint');q=p.get_location_at_spline_point(0,unreal.SplineCoordinateSpace.WORLD)
    center=a.get_actor_location();v=q*.85+center*.15
    hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(v.x,v.y,center.z+10000),unreal.Vector(v.x,v.y,center.z-100),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[],unreal.DrawDebugTrace.NONE,True)
    # Python returns HitResult; break_hit_result names are documented in the engine API.
    data=hit.to_tuple() if hit else ()
    hit_actor=data[9] if data and data[0] else None
    hits.append({'id':a.get_editor_property('building_id'),'hit_actor':hit_actor.get_actor_label() if hit_actor else None,'blocking':bool(data and data[0]),'expected_building':hit_actor==a})
assert all(r['expected_building'] for r in hits),hits
sample=next(a for a in buildings if plan[a.get_editor_property('building_id')]['pilot'])
old_floors=sample.get_editor_property('floor_count');old_height=sample.get_editor_property('floor_height_meters')
old_bounds=unreal.SystemLibrary.get_component_bounds(sample.get_editor_property('building_surface'))
sample.set_editor_property('floor_count',old_floors+1);sample.rebuild_building()
new_bounds=unreal.SystemLibrary.get_component_bounds(sample.get_editor_property('building_surface'))
height_change=(new_bounds[1].z-old_bounds[1].z)*2
assert abs(height_change-old_height*100)<.1,(height_change,old_height)
sample.set_editor_property('floor_count',old_floors);sample.rebuild_building()
report_edit={'added_floor_height_cm':height_change,'restored_without_saving':True}
report={'buildings':len(buildings),'roads':len(roads),'max_footprint_error_cm':max_error,'errors':errors,'pilot':pilot,'roof_collision_samples':hits,'editing_check':report_edit}
(ROOT/'Saved/Mazzarino80/buildings_validation.json').write_text(json.dumps(report,indent=2))
unreal.log('M80_BUILDINGS_REOPEN_VERIFIED '+json.dumps(report))
