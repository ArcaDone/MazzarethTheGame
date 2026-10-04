import unreal
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
paths=['/Game/Mazzarino80/Roads/M80_RoadSlab','/Game/Mazzarino80/RoadSource/Migrated/Lavica_curved','/Game/Mazzarino80/Roads/CorrectedBase/M80_Terreno_Corrected']
for path in paths:
    mesh=unreal.load_asset(path)
    unreal.log('M80_MESH_LOD '+path+' '+str(subsystem.get_lod_reduction_settings(mesh,0)))
    task=unreal.AssetExportTask()
    task.object=mesh
    task.filename=str(ROOT/'Saved/Mazzarino80'/f'{mesh.get_name()}_export.obj')
    task.automated=True
    task.prompt=False
    task.replace_identical=True
    task.exporter=unreal.StaticMeshExporterOBJ()
    unreal.Exporter.run_asset_export_task(task)
actor=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline) and a.get_actor_label().endswith('_1249463304'))
mesh=actor.get_components_by_class(unreal.SplineMeshComponent)[10]
unreal.log('M80_SEGMENT_BOUNDS '+str(unreal.SystemLibrary.get_component_bounds(mesh)))
unreal.log('M80_SEGMENT_RENDER '+str({k:str(mesh.get_editor_property(k)) for k in ['visible','hidden_in_game','render_in_main_pass','relative_location','relative_scale3d','relative_rotation','forced_lod_model','cast_shadow']}))
