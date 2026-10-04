import unreal,json
from pathlib import Path
root=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
roads=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline)]
corso=next(a for a in roads if a.get_actor_label().endswith('_1249463304'))
components=corso.get_components_by_class(unreal.SplineMeshComponent)
unreal.log('M80_BACKING_AUDIT '+str([(s.static_mesh.get_name(),str(s.get_start_position()),str(s.get_end_position()),str(s.get_start_scale()),str(s.get_start_offset()),s.is_visible()) for s in components[:4]]))
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'viewmode lit')
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(59000,-41000,48500),unreal.Rotator(pitch=-47,yaw=50,roll=0))
editor.set_selected_level_actors([])
unreal.log('M80_PRESENT_ROADS')
