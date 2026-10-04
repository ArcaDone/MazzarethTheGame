import unreal
from pathlib import Path
root=Path(r'D:\UE5Projects\GameAnimationSample')
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level('/Game/Levels/Mazzarino80_Panoramica')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=editor.get_all_level_actors()
roads=[a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline)]
assert len(roads)==1016
slab=unreal.load_asset('/Game/Mazzarino80/Roads/M80_RoadSlab')
for road in roads:
    if 'Corso Vittorio Emanuele' in road.road_name:
        road.set_editor_property('road_backing_mesh',slab)
        road.rebuild_road()
# OSM rings have mixed orientation; massing remains visible on either side.
mat=unreal.load_asset('/Game/Mazzarino80/Overview/M80_Edifici')
mat.set_editor_property('two_sided',True)
unreal.MaterialEditingLibrary.recompile_material(mat)
unreal.EditorAssetLibrary.save_loaded_asset(mat)
for path in ['/Game/Mazzarino80/Overview/M80_Strade','/Game/Mazzarino80/RoadSource/Migrated/Materials/Material']:
    paving=unreal.load_asset(path)
    paving.set_editor_property('two_sided',True)
    unreal.MaterialEditingLibrary.recompile_material(paving)
    unreal.EditorAssetLibrary.save_loaded_asset(paving)
for actor in actors:
    if actor.get_actor_label() in ('M80_Terreno','M80_Edifici'):actor.set_is_temporarily_hidden_in_editor(False)
assert level.save_current_level()
unreal.log('M80_ROADS_FINISH_SAVED')
exec(compile(root.joinpath('Scripts/mazzarino80_validate_spline_roads.py').read_text(),str(root/'Scripts/mazzarino80_validate_spline_roads.py'),'exec'))
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(74500,-10000,20200),unreal.Rotator(pitch=-55,yaw=60,roll=0))
