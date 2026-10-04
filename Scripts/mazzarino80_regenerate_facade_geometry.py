import unreal,json,runpy
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert levels.load_level('/Game/Levels/Mazzarino80_Panoramica')
for a in editor.get_all_level_actors():
    if isinstance(a,unreal.MazzarinoBuilding) and not str(a.get_editor_property('reconstruction_status')).startswith('Sostituito'):a.rebuild_building()
assert unreal.EditorLevelLibrary.save_current_level()
unreal.log('M80_GEOMETRY_REGENERATED')
runpy.run_path(str(ROOT/'Scripts/mazzarino80_check_facade_variety.py'))
