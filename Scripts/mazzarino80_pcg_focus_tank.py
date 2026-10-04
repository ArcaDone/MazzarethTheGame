"""Focus the validation viewport on one generated rooftop water tank."""
import json
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir())
lot='1249069213'
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
actor=next(a for a in actors if a.get_actor_label()=='BP_ProceduralBuilding_'+lot)
transform=next(c.get_instance_transform(0,world_space=True)
    for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    if c.get_instance_count()==1 and c.get_editor_property('static_mesh')
    and 'SM_Platform_Water_Tank_01' in c.get_editor_property('static_mesh').get_path_name())
p=transform.translation
camera=unreal.Vector(p.x+450,p.y-500,p.z+550)
target=unreal.Vector(p.x,p.y,p.z+40)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    camera,unreal.MathLibrary.find_look_at_rotation(camera,target))
