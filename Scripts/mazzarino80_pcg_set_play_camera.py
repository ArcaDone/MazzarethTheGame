"""Place the editor camera on the linked road beside one sample PCG house."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
lot='1249069204'
h=next(h for h in json.loads((root/'Saved/Mazzarino80/PCG/baseline_18.json').read_text(
    encoding='utf-8'))['houses'] if h['id']==lot)
p=h['footprint_world_cm']
edge=int(h['properties']['front_edge'])
a,b=p[edge],p[(edge+1)%len(p)]
front=unreal.Vector((a[0]+b[0])/2,(a[1]+b[1])/2,a[2])
source=next(x for x in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if isinstance(x,unreal.MazzarinoHistoricBuilding) and x.get_editor_property('lot_id')==lot)
road=source.get_editor_property('entrance_road')
if not road:
    raise RuntimeError('No linked road for '+lot)
spline=road.get_component_by_class(unreal.SplineComponent)
if not spline:
    raise RuntimeError('Road has no spline')
road_point=spline.find_location_closest_to_world_location(front,unreal.SplineCoordinateSpace.WORLD)
camera=unreal.Vector(road_point.x,road_point.y,road_point.z+180)
target=unreal.Vector(front.x,front.y,front.z+250)
rotation=unreal.MathLibrary.find_look_at_rotation(camera,target)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(camera,rotation)
report={'lot':lot,'road':road.get_actor_label(),'camera':[camera.x,camera.y,camera.z],
        'front':[front.x,front.y,front.z]}
(root/'Saved/Mazzarino80/PCG/set_play_camera.json').write_text(
    json.dumps(report,indent=2),encoding='utf-8')
