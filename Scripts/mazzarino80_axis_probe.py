import unreal,json,math
from pathlib import Path
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
road=next(a for a in editor.get_all_level_actors() if a.get_actor_label().endswith('_1249817820'))
rows=[]
for s in road.get_components_by_class(unreal.SplineMeshComponent):
    if s.static_mesh!=road.road_mesh:continue
    start,end=s.get_start_position(),s.get_end_position()
    ta,tb=s.get_start_tangent(),s.get_end_tangent()
    delta=end-start
    rows.append({'start':list(start.to_tuple()),'end':list(end.to_tuple()),'tangent_a':list(ta.to_tuple()),'tangent_b':list(tb.to_tuple()),'len':delta.length(),'dot_a':unreal.MathLibrary.dot_vector_vector(ta,delta),'dot_b':unreal.MathLibrary.dot_vector_vector(tb,delta),'up':list(s.get_spline_up_dir().to_tuple()),'roll_a':s.get_start_roll(),'roll_b':s.get_end_roll(),'scale':list(s.get_start_scale().to_tuple())})
Path(r'D:\UE5Projects\GameAnimationSample\Saved\Mazzarino80\axis_probe.json').write_text(json.dumps(rows,indent=2))
unreal.log('M80_AXIS_PROBE '+str(len(rows)))
