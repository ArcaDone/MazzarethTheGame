"""Undo the OBJ import Y reflection at actor level; spline coordinates remain geographic."""
import unreal
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=editor.get_all_level_actors()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name()=='Mazzarino80_Panoramica'
for label in ['M80_Terreno','M80_Edifici','M80_Strade']:
    actor=next(a for a in actors if a.get_actor_label()==label)
    actor.set_actor_scale3d(unreal.Vector(1,-1,1))
corso=next(a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline) and a.get_actor_label().endswith('_1249463304'))
spline=corso.get_component_by_class(unreal.SplineComponent)
p=spline.get_location_at_spline_point(12,unreal.SplineCoordinateSpace.WORLD)
start=next(a for a in actors if a.get_class().get_name()=='PlayerStart')
start.set_actor_location(unreal.Vector(p.x,p.y,p.z+150),False,True)
direction=spline.get_direction_at_spline_point(12,unreal.SplineCoordinateSpace.WORLD)
start.set_actor_rotation(unreal.Rotator(pitch=0,yaw=unreal.MathLibrary.conv_vector_to_rotator(direction).yaw,roll=0),False)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(74500,-10000,20200),unreal.Rotator(pitch=-55,yaw=60,roll=0))
unreal.log('M80_OBJ_Y_REFLECTION_CORRECTED')
