import unreal
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
roads=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline)]
corso=next(a for a in roads if a.get_actor_label().endswith('_1249463304'))
for road in roads:
    if 'Corso Vittorio Emanuele' not in road.road_name:continue
    for component in road.get_components_by_class(unreal.SplineMeshComponent):
        if component.static_mesh==road.road_backing_mesh:
            component.set_start_offset(unreal.Vector2D(0,-1),False)
            component.set_end_offset(unreal.Vector2D(0,-1),True)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(74500,-10000,20200),unreal.Rotator(pitch=-55,yaw=60,roll=0))
editor.set_selected_level_actors([])
unreal.log('M80_BACKING_HEIGHT_PROBE')
