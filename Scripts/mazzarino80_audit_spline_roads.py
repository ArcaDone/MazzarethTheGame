import json,math
from pathlib import Path
import unreal
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name()=='Mazzarino80_Panoramica'
roads=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline)]
source=json.loads((ROOT/'Research/Mazzarino80/generated/road_splines.json').read_text(encoding='utf-8'))
by_id={r['id'].replace('way/','')+(('_'+str(r['part'])) if r['part'] else ''):r for r in source}
items=[]
for actor in roads:
    suffix=actor.get_actor_label().rsplit('_',1)[-1]
    data=by_id.get(suffix)
    if data is None:continue
    spline=actor.get_component_by_class(unreal.SplineComponent)
    first=spline.get_location_at_spline_point(0,unreal.SplineCoordinateSpace.WORLD)
    expected=data['points_cm'][0]
    error=math.dist([first.x,first.y,first.z],expected)
    segments=actor.get_components_by_class(unreal.SplineMeshComponent)
    items.append({'label':actor.get_actor_label(),'error_cm':error,'actor_location':str(actor.get_actor_location()),
                  'spline_first':str(first),'expected':expected,'points':spline.get_number_of_spline_points(),
                  'segments':len(segments),'mesh':actor.road_mesh.get_path_name(),'material':actor.road_material.get_path_name(),
                  'first_segment_start':str(segments[0].get_start_position()) if segments else '',
                  'last_segment_end':str(segments[-1].get_end_position()) if segments else ''})
result={'world':world.get_name(),'road_count':len(roads),'max_first_point_error_cm':max(i['error_cm'] for i in items),'items':items}
(ROOT/'Saved/Mazzarino80/roads_audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
unreal.log('M80_ROAD_AUDIT '+str(result['max_first_point_error_cm']))
