import unreal
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cam=next((a for a in editor.get_all_level_actors() if a.get_actor_label()=='M80_Camera_Skyline'),None)
if not cam:cam=editor.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(73500,16000,23800))
cam.set_actor_label('M80_Camera_Skyline');cam.set_folder_path('Mazzarino80/Verifiche')
cam.set_actor_rotation(unreal.Rotator(pitch=-34,yaw=-42,roll=0),False)
cam.camera_component.set_field_of_view(70);cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
editor.set_selected_level_actors([])
for key in levels.get_viewport_config_keys():
    if str(key)=='FourPanes2x2.Viewport 2.Viewport0':levels.pilot_level_actor(cam,key)
levels.editor_invalidate_viewports()
unreal.log('M80_ROOF_VARIETY_VIEW')
