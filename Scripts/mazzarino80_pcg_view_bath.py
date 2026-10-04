"""Review the suspended privy from inside its generated courtyard."""
import json
import math
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
manifest=json.loads((root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))
points=manifest['houses']['1249069228']['stage_points']
details=points['Details']
gate=next(p for p in points['Openings'] if p['role']=='courtyard_gate_bar_07')['location_cm']
bath=next(p for p in details if p['role']=='external_bathroom')['location_cm']
dx,dy=bath[0]-gate[0],bath[1]-gate[1]
length=math.hypot(dx,dy)
location=unreal.Vector(gate[0]+dx/length*215,gate[1]+dy/length*215,gate[2]+70)
target=unreal.Vector(bath[0],bath[1],bath[2]+60)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    location,unreal.MathLibrary.find_look_at_rotation(location,target))
