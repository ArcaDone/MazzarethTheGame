"""Verify new instance rotations and editable spline persistence, restoring edits."""
import unreal,json,math
from pathlib import Path
root=Path(unreal.Paths.project_dir())
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
houses=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding)]
assert len(houses)==18
report={'houses':18,'tiles':0,'complete_balconies':0,'service_paths':0,'normalized_transforms':True}
for a in houses:
 for key in ['roof_tiles','balcony_modules']:
  c=a.get_editor_property(key)
  count=c.get_instance_count();report['tiles' if key=='roof_tiles' else 'complete_balconies']+=count
  for i in range(count):
   q=c.get_instance_transform(i,False).rotation
   assert abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1)<.0001,(a.get_actor_label(),key,i)
 report['service_paths']+=sum('M80ServicePath' in [str(t) for t in s.component_tags] for s in a.get_components_by_class(unreal.SplineComponent))
target=next(a for a in houses if any(s.get_name().startswith('Cavo_') for s in a.get_components_by_class(unreal.SplineComponent)))
path=next(s for s in target.get_components_by_class(unreal.SplineComponent) if s.get_name().startswith('Cavo_'))
space=unreal.SplineCoordinateSpace.LOCAL
original=path.get_location_at_spline_point(2,space)
try:
 path.set_location_at_spline_point(2,unreal.Vector(original.x,original.y,original.z-12),space,True)
 target.rebuild_house()
 retained=next(s for s in target.get_components_by_class(unreal.SplineComponent) if s.get_name()==path.get_name())
 assert abs(retained.get_location_at_spline_point(2,space).z-original.z+12)<.001
 pieces=[s for s in target.get_components_by_class(unreal.SplineMeshComponent) if s.get_attach_parent()==retained]
 assert len(pieces)>=2,(path.get_name(),[s.get_name() for s in target.get_components_by_class(unreal.SplineMeshComponent)])
 report['edited_cable_survives_rebuild']=True
finally:
 path.set_location_at_spline_point(2,original,space,True);target.rebuild_house()
report['test_edit_restored']=True
(root/'Saved/Mazzarino80/Historic/detail_validation.json').write_text(json.dumps(report,indent=2))
unreal.log('M80_DETAIL_VALIDATION '+json.dumps(report))
