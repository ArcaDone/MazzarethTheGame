import unreal,json
from pathlib import Path
root=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=editor.get_all_level_actors()
paths=['/Game/Mazzarino80/Overview/M80_Strade','/Game/Mazzarino80/RoadSource/Migrated/Materials/Material','/Game/Mazzarino80/Overview/M80_Terreno','/Game/Mazzarino80/Overview/M80_Edifici']
report={}
for path in paths:
    mat=unreal.load_asset(path)
    report[path]=mat.get_editor_property('two_sided')
    mat.set_editor_property('two_sided',True)
    unreal.MaterialEditingLibrary.recompile_material(mat)
root.joinpath('Saved/Mazzarino80/material_sides_original.json').write_text(json.dumps(report))
building=next(a for a in actors if a.get_actor_label()=='M80_Edifici')
building.set_is_temporarily_hidden_in_editor(True)
actor=next(a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline) and a.get_actor_label().endswith('_1249463304'))
spline=actor.get_component_by_class(unreal.SplineComponent)
p=spline.get_location_at_spline_point(10,unreal.SplineCoordinateSpace.WORLD)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(p+unreal.Vector(-1000,-1000,1800),unreal.Rotator(pitch=-45,yaw=45,roll=0))
unreal.log('M80_SIDES_DIAGNOSTIC '+str(report)+' camera '+str(p))
