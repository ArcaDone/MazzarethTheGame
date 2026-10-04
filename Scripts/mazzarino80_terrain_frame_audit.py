import unreal
mesh=unreal.load_asset('/Game/Mazzarino80/Overview/M80_Terreno1')
unreal.log('M80_TERRAIN_BOUNDS '+str(mesh.get_bounding_box()))
mesh=unreal.load_asset('/Game/Mazzarino80/Overview/M80_Edifici_Mesh')
unreal.log('M80_BUILDING_BOUNDS '+str(mesh.get_bounding_box()))
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(76000,-10000,21500),unreal.Rotator(pitch=-55,yaw=45,roll=0))
