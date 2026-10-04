import unreal
paths=['/Game/Mazzarino80/Overview/M80_Strade','/Game/Mazzarino80/Overview/M80_Edifici','/Game/Mazzarino80/RoadSource/Migrated/Materials/Material']
for path in paths:
    mat=unreal.load_asset(path)
    for prop in [unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET,unreal.MaterialProperty.MP_PIXEL_DEPTH_OFFSET]:
        node=unreal.MaterialEditingLibrary.get_material_property_input_node(mat,prop)
        unreal.log('M80_MATERIAL_INPUT '+path+' '+str(prop)+' '+str(node))
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for actor in editor.get_all_level_actors():
    if isinstance(actor,unreal.MazzarinoRoadSpline):
        for component in actor.get_components_by_class(unreal.SplineMeshComponent):component.set_cast_shadow(False)
unreal.log('M80_ROAD_SHADOW_PROBE')
