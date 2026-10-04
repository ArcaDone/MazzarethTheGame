import unreal
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
coord=unreal.SplineCoordinateSpace.LOCAL
count=0
for road in editor.get_all_level_actors():
    if not isinstance(road,unreal.MazzarinoRoadSpline) or 'Corso Vittorio Emanuele' not in road.road_name:continue
    spline=road.get_component_by_class(unreal.SplineComponent)
    length=spline.get_spline_length()
    def stable_direction(position,chord):
        distance=spline.get_distance_along_spline_at_location(position,coord)
        a=spline.get_location_at_distance_along_spline(max(0,distance-10),coord)
        b=spline.get_location_at_distance_along_spline(min(length,distance+10),coord)
        delta=b-a
        return delta/delta.length() if delta.length()>0.001 else chord/chord.length()
    for s in road.get_components_by_class(unreal.SplineMeshComponent):
        start,end=s.get_start_position(),s.get_end_position()
        ta,tb=s.get_start_tangent(),s.get_end_tangent()
        chord=end-start
        size=max(ta.length(),tb.length(),chord.length())
        if ta.length()<0.01:
            ta=stable_direction(start,chord)*size
            count+=1
        if tb.length()<0.01:
            tb=stable_direction(end,chord)*size
            count+=1
        s.set_start_and_end(start,ta,end,tb,True)
unreal.log('M80_NONZERO_TANGENT_PROBE '+str(count))
