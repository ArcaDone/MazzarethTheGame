import unreal

camera=unreal.Vector(74250,10500,17000)
target=unreal.Vector(75800,11150,17000)
rotation=unreal.MathLibrary.find_look_at_rotation(camera,target)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(camera,rotation)
