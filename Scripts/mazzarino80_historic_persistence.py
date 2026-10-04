"""Verify saved editable service paths and current modules after a real map reload."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir())
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
def snapshot():
 result={}
 for a in editor.get_all_level_actors():
  if not isinstance(a,unreal.MazzarinoHistoricBuilding):continue
  paths={}
  for c in a.get_components_by_class(unreal.SplineComponent):
   if 'M80ServicePath' not in [str(t) for t in c.component_tags]:continue
   paths[c.get_name()]=[[round(float(v),3) for v in (p.x,p.y,p.z)] for p in [c.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.LOCAL) for i in range(c.get_number_of_spline_points())]]
  result[a.get_editor_property('lot_id')]={'seed':a.get_editor_property('seed'),'paths':paths,'tiles':a.get_editor_property('roof_tiles').get_instance_count(),'balconies':a.get_editor_property('balcony_modules').get_instance_count(),'sill':a.get_editor_property('sill_projection'),'rotation':[round(v,5) for v in [a.get_actor_rotation().pitch,a.get_actor_rotation().roll]]}
 return result
before=snapshot();assert len(before)==18
assert levels.save_current_level()
assert levels.load_level('/Game/Levels/Mazzarino80_CaseStoriche_Campione')
after=snapshot()
assert before==after,('Map reload changed details',before,after)
report={'passed':True,'houses':len(after),'service_paths':sum(len(x['paths']) for x in after.values()),'tiles':sum(x['tiles'] for x in after.values()),'balconies':sum(x['balconies'] for x in after.values()),'upright':all(x['rotation']==[0.,0.] for x in after.values()),'before':before,'after':after}
(root/'Saved/Mazzarino80/Historic/persistence.json').write_text(json.dumps(report,indent=2))
exec(compile((root/'Scripts/mazzarino80_historic_detail_cameras.py').read_text(),'detail_cameras','exec'),{})
cam=next(a for a in editor.get_all_level_actors() if a.get_actor_label()=='M80_Dettaglio_Coppi')
for key in levels.get_viewport_config_keys():
 levels.eject_pilot_level_actor(key)
 if str(key).endswith('Viewport0'):levels.pilot_level_actor(cam,key)
levels.save_current_level()
unreal.AutomationLibrary.take_high_res_screenshot(1600,1000,str(root/'Saved/Mazzarino80/Preview/Historic/Details/detail_roof.png'),camera=cam,delay=3.,force_game_view=True)
unreal.log('M80_PERSISTENCE_PASSED')
