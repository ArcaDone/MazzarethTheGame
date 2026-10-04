import unreal,json
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level('/Game/Levels/Mazzarino80_Panoramica')
plan={r['id']:r for r in json.loads((ROOT/'Research/Mazzarino80/building_footprint_plan.json').read_text())}
for a in editor.get_all_level_actors():
    if not isinstance(a,unreal.MazzarinoBuilding):continue
    row=plan[a.get_editor_property('building_id')]
    if not row['pilot']:continue
    a.set_editor_property('front_edge_index',row['front_edge']);a.rebuild_building()
assert unreal.EditorLevelLibrary.save_current_level()

