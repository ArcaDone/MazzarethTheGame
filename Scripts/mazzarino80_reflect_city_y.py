"""Reflect the working city across world Y=0, retaining editable road splines."""
import unreal,json,math,shutil,datetime
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
LEVEL='/Game/Levels/Mazzarino80_Panoramica'
MARKER='M80_WorldYReflected_20260928'
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ue=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=ue.get_editor_world()
assert world.get_name()=='Mazzarino80_Panoramica'
actors=editor.get_all_level_actors()
roads=[a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline)]
terrain=next(a for a in actors if a.get_actor_label()=='M80_Terreno')
buildings=next(a for a in actors if a.get_actor_label()=='M80_Edifici')
assert MARKER not in [str(t) for t in terrain.tags],'City already reflected; refusing a second reflection'
assert len(roads)==1016
coord=unreal.SplineCoordinateSpace.LOCAL
worldcoord=unreal.SplineCoordinateSpace.WORLD
def reflect(p):return unreal.Vector(p.x,-p.y,p.z)
def reflect_rotation(r):return unreal.Rotator(pitch=r.pitch,yaw=-r.yaw,roll=-r.roll)
def close_vector(a,b,tolerance=0.03):return (a-b).length()<=tolerance
for a in roads+[terrain,buildings]:
    r=a.get_actor_rotation();s=a.get_actor_scale3d()
    assert abs(r.pitch)+abs(r.yaw)+abs(r.roll)<0.00001 and close_vector(s,unreal.Vector(1,1,1)),a.get_actor_label()
    assert not a.get_attach_parent_actor(),a.get_actor_label()

# These meshes are the same generated geometry with its local Y reflected by
# the OBJ importer. Duplicate them so that earlier maps and assets stay intact.
sources={'M80_Terreno':'/Game/Mazzarino80/Overview/M80_Terreno1','M80_Edifici':'/Game/Mazzarino80/Overview/M80_Edifici_Mesh'}
for a in (terrain,buildings):
    old=a.static_mesh_component.static_mesh.get_bounding_box()
    candidate=unreal.load_asset(sources[a.get_actor_label()]).get_bounding_box()
    assert close_vector(candidate.min,unreal.Vector(old.min.x,-old.max.y,old.min.z))
    assert close_vector(candidate.max,unreal.Vector(old.max.x,-old.min.y,old.max.z))
assert levels.save_current_level()
stamp=datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
backup=ROOT/'Saved/Mazzarino80/Backups'/('Before_Y_reflection_'+stamp)
backup.mkdir(parents=True,exist_ok=False)
shutil.copy2(ROOT/'Content/Levels/Mazzarino80_Panoramica.umap',backup/'Mazzarino80_Panoramica.umap')
camera=ue.get_level_viewport_camera_info()
snapshots={}
for a in roads:
    spline=a.get_component_by_class(unreal.SplineComponent)
    points=[spline.get_spline_point_at(i,coord) for i in range(spline.get_number_of_spline_points())]
    snapshots[a.get_actor_label()]={'location':a.get_actor_location(),'width':a.width_meters,'closed':spline.is_closed_loop(),'length':spline.get_spline_length(),'points':points,'world':[spline.get_location_at_spline_point(i,worldcoord) for i in range(len(points))]}
ignored=[a for a in actors if a!=terrain]
def ground(p):
    hit=unreal.SystemLibrary.line_trace_single(ue.get_editor_world(),unreal.Vector(p.x,p.y,60000),unreal.Vector(p.x,p.y,-40000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,unreal.DrawDebugTrace.NONE,True)
    values=hit.to_tuple() if hit else ()
    return values[4].z if values and values[0] and values[9]==terrain else None
samples=[]
for a in roads[::64]:
    s=a.get_component_by_class(unreal.SplineComponent)
    p=s.get_location_at_distance_along_spline(s.get_spline_length()/2,worldcoord)
    samples.append((p,ground(p)))
assert all(z is not None for p,z in samples),'Terrain sampling failed before reflection'

mesh_editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
for a in (terrain,buildings):
    label=a.get_actor_label()
    destination='/Game/Mazzarino80/Roads/ReflectedBase/'+label+'_WorldYReflected'
    mesh=unreal.EditorAssetLibrary.duplicate_asset(sources[label],destination)
    assert mesh,destination
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False
    mesh_editor.set_nanite_settings(mesh,nanite,True)
    mesh.set_material(0,a.static_mesh_component.get_material(0))
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh_editor.remove_collisions(mesh)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_location(reflect(a.get_actor_location()),False,True)

with unreal.ScopedSlowTask(len(roads),'Ribalto le strade insieme alla città') as progress:
    progress.make_dialog(False)
    for a in roads:
        progress.enter_progress_frame(1,a.road_name)
        saved=snapshots[a.get_actor_label()]
        spline=a.get_component_by_class(unreal.SplineComponent)
        a.set_actor_location(reflect(saved['location']),False,True)
        for i,p in enumerate(saved['points']):
            spline.set_location_at_spline_point(i,reflect(p.position),coord,False)
            if p.type==unreal.SplinePointType.CURVE_CUSTOM_TANGENT:
                spline.set_tangents_at_spline_point(i,reflect(p.arrive_tangent),reflect(p.leave_tangent),coord,False)
        spline.update_spline()
        a.rebuild_road()

for a in actors:
    if a in roads or a in (terrain,buildings):continue
    # Includes disabled reference roads, PlayerStart, and scene lighting.
    p=a.get_actor_location();r=a.get_actor_rotation();scale=a.get_actor_scale3d()
    a.set_actor_location(reflect(p),False,True)
    a.set_actor_rotation(reflect_rotation(r),False)
    if isinstance(a,unreal.StaticMeshActor):a.set_actor_scale3d(unreal.Vector(scale.x,-scale.y,scale.z))

errors=[];length_error=0;zero=0
for a in roads:
    saved=snapshots[a.get_actor_label()]
    s=a.get_component_by_class(unreal.SplineComponent)
    assert a.width_meters==saved['width'] and s.is_closed_loop()==saved['closed']
    assert s.get_number_of_spline_points()==len(saved['world'])
    length_error=max(length_error,abs(s.get_spline_length()-saved['length']))
    for i,p in enumerate(saved['world']):
        error=(s.get_location_at_spline_point(i,worldcoord)-reflect(p)).length()
        if error>0.03:errors.append([a.get_actor_label(),i,error])
        assert close_vector(s.get_scale_at_spline_point(i),saved['points'][i].scale)
    for c in a.get_components_by_class(unreal.SplineMeshComponent):
        zero+=int(c.get_start_tangent().length()<0.01)+int(c.get_end_tangent().length()<0.01)
assert not errors and zero==0,(errors[:3],zero)
assert length_error<0.1,length_error
height_errors=[abs(ground(reflect(p))-z) if ground(reflect(p)) is not None else float('inf') for p,z in samples]
assert max(height_errors)<0.1,height_errors
terrain.tags=list(terrain.tags)+[MARKER]
assert levels.save_current_level()
assert levels.load_level('/Game/Levels/Main')
assert levels.load_level(LEVEL)
reopened=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline)]
assert len(reopened)==len(roads)
max_error=0
for a in reopened:
    saved=snapshots[a.get_actor_label()]
    s=a.get_component_by_class(unreal.SplineComponent)
    assert s.get_number_of_spline_points()==len(saved['world']) and a.width_meters==saved['width']
    for i,p in enumerate(saved['world']):max_error=max(max_error,(s.get_location_at_spline_point(i,worldcoord)-reflect(p)).length())
assert max_error<0.03,max_error
ue.set_level_viewport_camera_info(reflect(camera[0]),reflect_rotation(camera[1]))
editor.set_selected_level_actors([])
result={'transformation':'world (x,y,z) -> (x,-y,z)','roads':len(reopened),'points':sum(len(v['points']) for v in snapshots.values()),'widths_and_point_scales_preserved':True,'maximum_spline_length_error_cm':length_error,'maximum_reopened_position_error_cm':max_error,'terrain_samples':len(samples),'maximum_terrain_height_error_cm':max(height_errors),'zero_segment_end_directions':zero,'saved_and_reopened':True,'backup':str(backup)}
(ROOT/'Saved/Mazzarino80/y_reflection_validation.json').write_text(json.dumps(result,indent=2))
unreal.log('M80_CITY_Y_REFLECTION_VERIFIED '+str(result))
