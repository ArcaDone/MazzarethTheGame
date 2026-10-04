"""Use deformable road meshes and conform points to the actual terrain collision."""
import json,math
from pathlib import Path
import unreal
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name()=='Mazzarino80_Panoramica'
actors=editor.get_all_level_actors()
roads=[a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline)]
terrain=next(a for a in actors if a.get_actor_label()=='M80_Terreno')
ignored=[a for a in actors if a!=terrain]
subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
for path in ['/Game/Mazzarino80/RoadSource/Migrated/Lavica_curved','/Game/Mazzarino80/Roads/M80_RoadSlab']:
    mesh=unreal.load_asset(path)
    settings=mesh.get_editor_property('nanite_settings')
    settings.enabled=False
    subsystem.set_nanite_settings(mesh,settings,True)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
def ground(x,y):
    result=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,50000),unreal.Vector(x,y,-30000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,unreal.DrawDebugTrace.NONE,True)
    values=result.to_tuple() if result else ()
    return values[4].z if values and values[0] and values[9]==terrain else None
fixed=0;maximum_change=0
with unreal.ScopedSlowTask(len(roads),'Adatto la pavimentazione al rilievo presente') as progress:
    progress.make_dialog(False)
    for actor in roads:
        progress.enter_progress_frame(1,actor.road_name)
        spline=actor.get_component_by_class(unreal.SplineComponent)
        spline.set_editor_property('draw_debug',False)
        updates=[]
        for index in range(spline.get_number_of_spline_points()):
            p=spline.get_location_at_spline_point(index,unreal.SplineCoordinateSpace.WORLD)
            direction=spline.get_direction_at_spline_point(index,unreal.SplineCoordinateSpace.WORLD)
            norm=math.hypot(direction.x,direction.y)
            px,py=(-direction.y/norm,direction.x/norm) if norm>0 else (0,1)
            half=actor.width_meters*50
            heights=[ground(p.x+px*half*f,p.y+py*half*f) for f in (-1,0,1)]
            valid=[h for h in heights if h is not None]
            if not valid:continue
            z=max(valid)+35
            maximum_change=max(maximum_change,abs(z-p.z))
            updates.append((index,unreal.Vector(p.x,p.y,z)))
        for index,p in updates:spline.set_location_at_spline_point(index,p,unreal.SplineCoordinateSpace.WORLD,False)
        spline.update_spline()
        actor.rebuild_road()
        fixed+=len(updates)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
(ROOT/'Saved/Mazzarino80/roads_terrain_conform.json').write_text(json.dumps({'points_conformed':fixed,'maximum_z_change_cm':maximum_change,'nanite_disabled_on_road_meshes':True},indent=2),encoding='utf-8')
editor.set_selected_level_actors([])
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(74500,-10000,20200),unreal.Rotator(pitch=-55,yaw=60,roll=0))
unreal.log('M80_ROAD_SURFACES_FINALIZED '+str(fixed))
