import unreal
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Levels/Mazzarino80_Panoramica')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
roads=[a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline)]
unreal.log('M80_ROADS_REOPENED '+str(len(roads))+' segments '+str(sum(len(a.get_components_by_class(unreal.SplineMeshComponent)) for a in roads)))
for a in actors:
    if a.get_actor_label() in ('M80_Terreno','M80_Edifici'):a.set_is_temporarily_hidden_in_editor(False)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(74500,-10000,20200),unreal.Rotator(pitch=-55,yaw=60,roll=0))
