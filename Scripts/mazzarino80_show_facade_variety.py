import unreal
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cam=next(a for a in editor.get_all_level_actors() if a.get_actor_label()=='M80_Camera_Confronto_90')
editor.set_selected_level_actors([])
for key in levels.get_viewport_config_keys():
    if str(key)=='FourPanes2x2.Viewport 2.Viewport0':levels.pilot_level_actor(cam,key)
levels.editor_invalidate_viewports()
assert levels.save_current_level()
unreal.log('M80_COMPARISON_CAMERA_90_PILOTED')
