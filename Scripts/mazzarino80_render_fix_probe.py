import unreal
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=editor.get_all_level_actors()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'r.SplineMesh.NoRecreateProxy 0')
actor=next(a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline) and a.get_actor_label().endswith('_1249463304'))
actor.rebuild_road()
for mesh in actor.get_components_by_class(unreal.SplineMeshComponent):
    mesh.set_boundary_min(0,False)
    mesh.set_boundary_max(0,True)
    mesh.set_material(0,unreal.load_asset('/Engine/EngineMaterials/DefaultMaterial'))
unreal.log('M80_RENDER_PROBE')
