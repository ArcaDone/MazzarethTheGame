"""Replace the overview road ribbons with individual editable road actors."""
import json, re
from pathlib import Path
import unreal
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
LEVEL='/Game/Levels/Mazzarino80_Panoramica'
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level(LEVEL)
assert hasattr(unreal,'MazzarinoRoadSpline'),'Road module not loaded'
existing=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline)]
assert not (ROOT/'Saved/Mazzarino80/roads_import.json').exists(),'Roads already installed; do not overwrite manual edits'
for actor in existing: editor.destroy_actor(actor)
data=json.loads((ROOT/'Research/Mazzarino80/generated/road_splines.json').read_text(encoding='utf-8'))
source='/Game/Mazzarino80/RoadSource/Migrated/'
lava=unreal.load_asset(source+'Lavica_curved')
lava_material=unreal.load_asset(source+'Materials/Material')
assert lava and lava_material
task=unreal.AssetImportTask()
task.filename=str(ROOT/'Research/Mazzarino80/generated/M80_RoadSlab.obj')
task.destination_path='/Game/Mazzarino80/Roads'
task.destination_name='M80_RoadSlab'
task.automated=True
task.replace_existing=False
task.save=True
task.set_editor_property('async_',False)
options=unreal.FbxImportUI()
options.import_mesh=True
options.import_materials=False
options.import_textures=False
options.automated_import_should_detect_type=False
options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
options.static_mesh_import_data.combine_meshes=True
task.options=options
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
slab=unreal.load_asset('/Game/Mazzarino80/Roads/M80_RoadSlab')
if not slab:
    slab=next((unreal.load_asset(p) for p in task.imported_object_paths if isinstance(unreal.load_asset(p),unreal.StaticMesh)),None)
assert slab,task.imported_object_paths
neutral=unreal.load_asset('/Game/Mazzarino80/Overview/M80_Strade')
assert neutral
for mesh in (lava,slab):
    body=mesh.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
created=[]
with unreal.ScopedSlowTask(len(data),'Creo le strade modificabili di Mazzarino') as progress:
    progress.make_dialog(False)
    for index,road in enumerate(data):
        progress.enter_progress_frame(1,road['name'] or road['id'])
        points=road['points_cm']
        origin=unreal.Vector(*points[0])
        actor=editor.spawn_actor_from_class(unreal.MazzarinoRoadSpline,origin)
        assert actor
        name=road['name'] or ('Senza_nome_'+road['highway'])
        identifier=road['id'].replace('way/','')
        label='M80_Strada_'+name+'_'+identifier+(('_'+str(road['part'])) if road['part'] else '')
        actor.set_actor_label(label)
        actor.set_folder_path('Mazzarino80/Strade_spline/'+('Corso_Vittorio_Emanuele' if road['corso'] else road['highway']))
        actor.set_editor_properties({'width_meters':road['width_m'],'road_name':name,
                                     'mesh_vertical_scale':0.1 if road['corso'] else 1.0,
                                     'segment_length_meters':10.0,'road_collision':True,
                                     'road_mesh':lava if road['corso'] else slab,
                                     'road_material':lava_material if road['corso'] else neutral})
        actor.set_editor_property('tags',[unreal.Name('OSM_'+identifier),unreal.Name('OSM_'+road['highway'])])
        spline=actor.get_component_by_class(unreal.SplineComponent)
        spline.set_spline_points([unreal.Vector(p[0]-origin.x,p[1]-origin.y,p[2]-origin.z) for p in points],unreal.SplineCoordinateSpace.LOCAL,False)
        for i in range(len(points)):
            spline.set_spline_point_type(i,unreal.SplinePointType.CURVE_CLAMPED,False)
        spline.set_closed_loop(road['closed'],False)
        spline.set_editor_property('spline_has_been_edited',True)
        spline.update_spline()
        actor.rebuild_road()
        created.append({'label':label,'id':road['id'],'corso':road['corso'],'points':len(points),'segments':actor.get_road_segment_count(),'path':actor.get_path_name()})
        if index%100==0:unreal.log('M80_ROADS_PROGRESS '+str(index)+'/'+str(len(data)))
assert len(created)==len(data) and all(a['segments']>0 for a in created)
old=next(a for a in editor.get_all_level_actors() if a.get_actor_label()=='M80_Strade')
old.set_actor_hidden_in_game(True)
old.set_is_temporarily_hidden_in_editor(True)
old.set_actor_enable_collision(False)
old.set_folder_path('Mazzarino80/Riferimento_strade_precedente_disattivato')
for component in old.get_components_by_class(unreal.PrimitiveComponent):component.set_visibility(False,True)
assert levels.save_current_level()
(ROOT/'Saved/Mazzarino80/roads_import.json').write_text(json.dumps({'level':LEVEL,'roads':len(created),'total_segments':sum(a['segments'] for a in created),'items':created},indent=2,ensure_ascii=False),encoding='utf-8')
corso=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline) and 'Corso Vittorio Emanuele' in a.road_name]
editor.set_selected_level_actors(corso[:1])
camera=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
camera.set_level_viewport_camera_info(unreal.Vector(82000,-25000,23000),unreal.Rotator(pitch=-35,yaw=85,roll=0))
unreal.log('M80_ROADS_IMPORT_DONE '+str(len(created)))
