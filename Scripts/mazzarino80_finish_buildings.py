import unreal,json
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level('/Game/Levels/Mazzarino80_Panoramica')
plan={r['id']:r for r in json.loads((ROOT/'Research/Mazzarino80/building_footprint_plan.json').read_text())}
for a in editor.get_all_level_actors():
    if not isinstance(a,unreal.MazzarinoBuilding):continue
    row=plan[a.get_editor_property('building_id')]
    if not row['pilot']:continue
    a.set_editor_property('front_edge_index',row['front_edge']);a.rebuild_building()
assert unreal.EditorLevelLibrary.save_current_level()
# Add the prepared CasaFloresta building to the catalogue, preserving the existing ten models.
assert levels.load_level('/Game/Levels/Mazzarino80_Catalogo')
label='CasaFloresta_Comune'
if not any(a.get_actor_label()==label for a in editor.get_all_level_actors()):
    cls=unreal.load_class(None,'/Game/Mazzarino80/Library/Comune/Esercitazioni/CasaFloresta/CasaFloresta.CasaFloresta_C');assert cls
    a=editor.spawn_actor_from_class(cls,unreal.Vector(0,80000,0));assert a
    a.set_actor_label(label);a.set_folder_path('Risorse_Comune/CasaFloresta');a.tags=['M80_ComuneReusableBuilding','Da_adattare_ai_perimetri']
    center,extent=a.get_actor_bounds(False);a.set_actor_location(a.get_actor_location()+unreal.Vector(0,0,extent.z-center.z+50),False,False)
    (ROOT/'Research/Mazzarino80/casa_floresta_catalog_info.json').write_text(json.dumps({'class':cls.get_path_name(),'components':len(a.get_components_by_class(unreal.StaticMeshComponent)),'extent_cm':list(extent.to_tuple()),'location_cm':list(a.get_actor_location().to_tuple())},indent=2))
assert unreal.EditorLevelLibrary.save_current_level()
unreal.log('M80_BUILDINGS_FINISH_DONE')
