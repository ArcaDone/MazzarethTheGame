"""Aim the editor viewport at a representative PCG house."""
import math
import unreal

actor=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
           if a.get_actor_label()=='BP_ProceduralBuilding_1249068307')
target=actor.get_actor_location()
dx,dy,dz=2500.0,-3500.0,1600.0
camera=unreal.Vector(target.x+dx,target.y+dy,target.z+dz)
pitch=math.degrees(math.atan2(-dz,math.hypot(dx,dy)))
yaw=math.degrees(math.atan2(-dy,-dx))
unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera,unreal.Rotator(pitch=pitch,yaw=yaw,roll=0))
