"""Face the sample route at spawn and frame it in the editor viewport."""

import unreal


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == "Mazzarino80_Base"
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
start = next(a for a in actors if a.get_class().get_name() == "PlayerStart")
start.set_actor_rotation(unreal.Rotator(pitch=0, yaw=23, roll=0), False)
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
if hasattr(unreal.EditorLevelLibrary, "set_level_viewport_camera_info"):
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(
        unreal.Vector(80000, -16000, 26000),
        unreal.Rotator(pitch=-29, yaw=55, roll=0))
unreal.log("MAZZARINO80_PLAYER_START_FACES_PATH")
