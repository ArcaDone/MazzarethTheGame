import unreal
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=editor.get_all_level_actors()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name()=='Mazzarino80_Panoramica'
for name,material in [('M80_Terreno','M80_Terreno'),('M80_Edifici','M80_Edifici')]:
    task=unreal.AssetImportTask()
    task.filename=str(ROOT/'Research/Mazzarino80/generated'/f'{name}_Corrected.obj')
    task.destination_path='/Game/Mazzarino80/Roads/CorrectedBase'
    task.destination_name=name+'_Corrected'
    task.automated=True
    task.replace_existing=False
    task.save=True
    task.set_editor_property('async_',False)
    options=unreal.FbxImportUI()
    options.import_materials=False
    options.import_textures=False
    options.import_mesh=True
    options.automated_import_should_detect_type=False
    options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
    options.static_mesh_import_data.combine_meshes=True
    task.options=options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes=[unreal.load_asset(p) for p in task.imported_object_paths if isinstance(unreal.load_asset(p),unreal.StaticMesh)]
    assert len(meshes)==1,task.imported_object_paths
    mesh=meshes[0]
    subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    settings=mesh.get_editor_property('nanite_settings')
    settings.enabled=False
    subsystem.set_nanite_settings(mesh,settings,True)
    mesh.set_material(0,unreal.load_asset('/Game/Mazzarino80/Overview/'+material))
    body=mesh.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    subsystem.remove_collisions(mesh)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    actor=next(a for a in actors if a.get_actor_label()==name)
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.set_actor_scale3d(unreal.Vector(1,1,1))
    unreal.log('M80_CORRECTED_ASSET '+mesh.get_path_name()+' '+str(mesh.get_bounding_box()))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log('M80_CORRECTED_BASE_IMPORTED')
