import unreal,json,math
from pathlib import Path
root=Path(unreal.Paths.project_dir());out=root/'Saved/Mazzarino80/Historic'
e=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);actors=e.get_all_level_actors()
houses=[a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)]
old={a.get_editor_property('building_id'):a for a in actors if isinstance(a,unreal.MazzarinoBuilding)}
archived=json.loads((out/'previous_lots.json').read_text()) if (out/'previous_lots.json').exists() else {}
def ring(a):
    s=a.get_editor_property('footprint')
    return [s.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD).to_tuple() for i in range(s.get_number_of_spline_points())]
report={'map':unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name(),'houses':[],'max_lot_xy_delta_cm':0.,'landmarks_preserved':True,'terrain_z_cm':None}
for a in houses:
    key=a.get_editor_property('lot_id');p=ring(a);q=ring(old[key]) if key in old else archived[key]['points'];assert len(p)==len(q)
    delta=max(math.dist(x[:2],y[:2]) for x,y in zip(p,q));assert delta<.01,(key,delta)
    report['max_lot_xy_delta_cm']=max(report['max_lot_xy_delta_cm'],delta)
    report['houses'].append({'id':key,'family':str(a.get_editor_property('resolved_family')),'volumes':a.get_editor_property('generated_volumes'),'openings':a.get_editor_property('generated_openings'),'balconies':a.get_editor_property('generated_balconies'),'doors':a.get_editor_property('door_panels').get_instance_count(),'location':list(a.get_actor_location().to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple())})
baseline=json.loads((out/'generation.json').read_text())['landmarks_before']
for b in baseline:
    a=next(a for a in actors if a.get_actor_label()==b['label'])
    assert math.dist(a.get_actor_location().to_tuple(),b['location'])<.01
    assert math.dist(a.get_actor_rotation().to_tuple(),b['rotation'])<.001
    assert math.dist(a.get_actor_scale3d().to_tuple(),b['scale'])<.00001
g=next(a for a in actors if a.get_actor_label()=='M80_Terreno');report['terrain_z_cm']=g.get_actor_location().z;assert abs(report['terrain_z_cm']-17100)<.01
(out/'integrity.json').write_text(json.dumps(report,indent=2))
unreal.log('M80_HISTORIC_INTEGRITY '+json.dumps({k:v for k,v in report.items() if k!='houses'}))
