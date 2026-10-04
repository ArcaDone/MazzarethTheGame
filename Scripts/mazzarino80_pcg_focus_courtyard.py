"""Focus the editor on the gate or the small external bathroom."""
import json
import math
from pathlib import Path
import unreal

LOT='1249069228'
MODE='bath'
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
source=next(a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)
            and a.get_editor_property('lot_id')==LOT)
target=next(a for a in actors if a.get_actor_label()=='BP_ProceduralBuilding_'+LOT)
front=source.get_editor_property('front_edge')
spline=source.get_editor_property('footprint')
points=[spline.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD)
        for i in range(spline.get_number_of_spline_points())]
a,b=points[front],points[(front+1)%len(points)]
dx,dy=b.x-a.x,b.y-a.y
length=math.hypot(dx,dy)
signed=sum(v.x*points[(i+1)%len(points)].y-points[(i+1)%len(points)].x*v.y
           for i,v in enumerate(points))
out=(dy/length,-dx/length) if signed>0 else (-dy/length,dx/length)
key='SM_metal_gate_01' if MODE=='gate' else 'Corridor_A_Box02_Ex'
matches=[]
for comp in target.get_components_by_class(unreal.InstancedStaticMeshComponent):
    mesh=comp.get_editor_property('static_mesh')
    if mesh and key in mesh.get_path_name():
        matches += [comp.get_instance_transform(i,world_space=True)
                    for i in range(comp.get_instance_count())]
if len(matches)!=1:
    raise RuntimeError('Expected exactly one '+key+' instance, got '+str(len(matches)))
p=matches[0].translation
if MODE=='gate':
    camera=unreal.Vector(p.x-out[0]*420,p.y-out[1]*420,p.z+180)
    look=unreal.Vector(p.x,p.y,p.z+155)
else:
    bounds=unreal.load_asset('/Game/City_of_Brass_Enviroment/Meshes/Corridor_A/Corridor_A_Box02_Ex').get_bounds()
    bottom=(bounds.origin.z-bounds.box_extent.z)*matches[0].scale3d.z
    camera=unreal.Vector(p.x+out[0]*260,p.y+out[1]*260,p.z+bottom+180)
    look=unreal.Vector(p.x,p.y,p.z+bottom+140)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    camera,unreal.MathLibrary.find_look_at_rotation(camera,look))
report={'lot':LOT,'mode':MODE,'mesh':key,
        'location_cm':[p.x,p.y,p.z],
        'camera_cm':[camera.x,camera.y,camera.z]}
path=Path(unreal.Paths.project_dir())/'Saved/Mazzarino80/PCG/courtyard_focus.json'
path.write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_COURTYARD_FOCUS '+str(path))
