import unreal
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
roads=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoRoadSpline)]
cube=unreal.load_asset('/Engine/BasicShapes/Cube')
for road in roads:
    if 'Corso Vittorio Emanuele' not in road.road_name:continue
    road.set_editor_property('road_backing_mesh',cube)
    road.rebuild_road()
unreal.log('M80_CUBE_SLAB_PROBE')
