import unreal, json, math, hashlib, struct
from pathlib import Path
root=Path(unreal.Paths.project_dir());out=root/'Saved/Mazzarino80/Historic'
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world.get_name()!='Mazzarino80_CaseStoriche_Campione':assert levels.load_level('/Game/Levels/Mazzarino80_CaseStoriche_Campione')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=editor.get_all_level_actors();houses=[a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)]
assert len(houses)==18
def sections(a):
    c=a.get_editor_property('surface')
    return [(i,unreal.ProceduralMeshLibrary.get_section_from_procedural_mesh(c,i)) for i in range(c.get_num_sections())]
def digest(a):
    values=[]
    for i,data in sections(a):values.append([i,[list(v.to_tuple()) for v in data[0]],list(data[1])])
    for key in ['stone_details','iron_details','wood_details','glass_details','street_details','life_details','door_panels','pots','roof_tiles','balcony_modules']:
        c=a.get_editor_property(key)
        values.append([key,[[list(t.translation.to_tuple()),list(t.rotation.to_tuple()),list(t.scale3d.to_tuple())] for t in [c.get_instance_transform(i,False) for i in range(c.get_instance_count())]]])
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()
report={'map':'/Game/Levels/Mazzarino80_CaseStoriche_Campione','houses':[],'errors':[],'geometry':{'triangles':0,'float32_degenerate':0},'support_tests':{},'route':{}}
for a in houses:
    a.update_support();error=a.get_editor_property('geometry_error')
    if error:report['errors'].append([a.get_actor_label(),error])
    key=a.get_editor_property('lot_id');h=digest(a);a.rebuild_house();assert digest(a)==h,('non deterministic',key)
    for i,data in sections(a):
        verts=[struct.unpack('fff',struct.pack('fff',v.x,v.y,v.z)) for v in data[0]];idx=data[1]
        for j in range(0,len(idx),3):
            points=[verts[idx[j+k]] for k in range(3)];report['geometry']['triangles']+=1
            u=[points[1][d]-points[0][d] for d in range(3)];v=[points[2][d]-points[0][d] for d in range(3)]
            cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            if sum(x*x for x in cross)<.00001:report['geometry']['float32_degenerate']+=1
    rot=a.get_actor_rotation();assert abs(rot.pitch)<.001 and abs(rot.roll)<.001
    report['houses'].append({'id':key,'family':str(a.get_editor_property('resolved_family')),'volumes':a.get_editor_property('generated_volumes'),'openings':a.get_editor_property('generated_openings'),'balconies':a.get_editor_property('generated_balconies'),'hash':h,'z':a.get_actor_location().z})
base={a.get_path_name():digest(a) for a in houses};target=houses[0];seed=target.get_editor_property('seed');target.set_editor_property('seed',seed+1);target.rebuild_house()
assert digest(target)!=base[target.get_path_name()]
assert all(digest(a)==base[a.get_path_name()] for a in houses if a!=target)
target.set_editor_property('seed',seed);target.rebuild_house();assert digest(target)==base[target.get_path_name()]
report['single_seed_isolation']=True
road=target.get_editor_property('entrance_road');spline=road.get_editor_property('spline');original=[]
for i in range(spline.get_number_of_spline_points()):original.append(spline.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.LOCAL))
startz=target.get_actor_location().z
for i,p in enumerate(original):spline.set_location_at_spline_point(i,unreal.Vector(p.x,p.y,p.z+80),unreal.SplineCoordinateSpace.LOCAL,False)
spline.update_spline();road.rebuild_road();target.update_support()
delta=target.get_actor_location().z-startz
assert abs(delta-80)<.01,delta
assert abs(target.get_actor_rotation().pitch)<.001 and abs(target.get_actor_rotation().roll)<.001
report['support_tests']['road_plus_80_cm']={'house_delta_cm':delta,'upright':True}
for i,p in enumerate(original):spline.set_location_at_spline_point(i,p,unreal.SplineCoordinateSpace.LOCAL,False)
spline.update_spline();road.rebuild_road()
for a in houses:a.update_support()
terrain=target.get_editor_property('ground_actor');groundloc=terrain.get_actor_location();before={a.get_path_name():digest(a) for a in houses};beforez={a.get_path_name():a.get_actor_location().z for a in houses}
gc=terrain.get_component_by_class(unreal.StaticMeshComponent);mobility=gc.mobility;gc.set_mobility(unreal.ComponentMobility.MOVABLE)
terrain.set_actor_location(unreal.Vector(groundloc.x,groundloc.y,groundloc.z+60),False,False)
for a in houses:a.update_support()
affected=sum(digest(a)!=before[a.get_path_name()] or abs(a.get_actor_location().z-beforez[a.get_path_name()])>.5 for a in houses)
assert affected>0
report['support_tests']['terrain_plus_60_cm']={'geometry_or_position_updated_houses':affected,'house_z_deltas_cm':{a.get_editor_property('lot_id'):a.get_actor_location().z-beforez[a.get_path_name()] for a in houses},'all_upright':all(abs(a.get_actor_rotation().pitch)<.001 and abs(a.get_actor_rotation().roll)<.001 for a in houses)}
terrain.set_actor_location(groundloc,False,False)
gc.set_mobility(mobility)
for a in houses:a.update_support()
assert all(abs(a.get_actor_location().z-next(h['z'] for h in report['houses'] if h['id']==a.get_editor_property('lot_id')))<.01 for a in houses)
report['support_tests']['restored']=True
assert not report['errors'] and report['geometry']['float32_degenerate']==0,report
(out/'validation.json').write_text(json.dumps(report,indent=2))
unreal.log('M80_HISTORIC_VALIDATION '+json.dumps({k:v for k,v in report.items() if k!='houses'}))
