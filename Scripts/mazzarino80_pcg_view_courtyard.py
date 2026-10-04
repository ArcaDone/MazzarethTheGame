"""Frame the courtyard house from pedestrian height for visual review."""
import json
import math
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
rows=json.loads((root/'Research/Mazzarino80/PCG/Buildings_Test18.json').read_text(encoding='utf-8'))['buildings']
row=next(r for r in rows if r['building_id']=='1249069228')
points=row['footprint_world_cm']
front=int(row['front_edge'])
a,b=points[front],points[(front+1)%len(points)]
dx,dy=b[0]-a[0],b[1]-a[1]
length=math.hypot(dx,dy)
signed=sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))
outward=(dy/length,-dx/length) if signed>0 else (-dy/length,dx/length)
mid=((a[0]+b[0])*.5,(a[1]+b[1])*.5)
location=unreal.Vector(mid[0]+outward[0]*350,mid[1]+outward[1]*350,a[2]+180)
target=unreal.Vector(mid[0],mid[1],a[2]+180)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    location,unreal.MathLibrary.find_look_at_rotation(location,target))
