import unreal
actor=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
           if a.get_actor_label()=='BP_ProceduralBuilding_1249069275')
pcg=actor.get_component_by_class(unreal.PCGComponent)
pcg.cleanup(True)
