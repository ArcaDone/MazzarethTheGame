import unreal,json
from pathlib import Path
root=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=editor.get_all_level_actors()
for path,flag in json.loads(root.joinpath('Saved/Mazzarino80/material_sides_original.json').read_text()).items():
    mat=unreal.load_asset(path)
    mat.set_editor_property('two_sided',flag)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
for actor in actors:
    if actor.get_actor_label() in ('M80_Terreno','M80_Edifici'):actor.set_is_temporarily_hidden_in_editor(False)
    if isinstance(actor,unreal.MazzarinoRoadSpline) and actor.get_actor_label().endswith('_1249463304'):actor.rebuild_road()
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log('M80_DIAGNOSTIC_RESTORED')
