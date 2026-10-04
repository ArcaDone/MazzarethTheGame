import unreal
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=editor.get_all_level_actors()
terrain=next(a for a in actors if a.get_actor_label()=='M80_Terreno')
terrain.set_is_temporarily_hidden_in_editor(True)
road=next(a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline) and a.get_actor_label().endswith('_1249463304'))
editor.set_selected_level_actors([road])
unreal.log('M80_ROADS_ISOLATED')
