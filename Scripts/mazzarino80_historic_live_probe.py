"""Verify automatic support updates while viewport realtime remains disabled.
Runs in the open editor, restores every temporary change, never saves test offsets.
"""
import unreal,time,json
from pathlib import Path
e=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert w.get_name()=='Mazzarino80_CaseStoriche_Campione'
houses=[a for a in e.get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding)]
assert len(houses)==18
ground=houses[0].get_editor_property('ground_actor');gc=ground.get_component_by_class(unreal.StaticMeshComponent)
originalmobility=gc.mobility;originalground=ground.get_actor_location()
target=next(a for a in houses if a.get_editor_property('lot_id')=='1249069275')
road=target.get_editor_property('entrance_road');s=road.get_editor_property('spline')
originalpoints=[s.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.LOCAL) for i in range(s.get_number_of_spline_points())]
def shape(a):
    c=a.get_editor_property('surface');return [[list(v.to_tuple()) for v in unreal.ProceduralMeshLibrary.get_section_from_procedural_mesh(c,i)[0]] for i in range(c.get_num_sections())]
baseline={a.get_path_name():shape(a) for a in houses};z=target.get_actor_location().z
baseline_z={a.get_path_name():a.get_actor_location().z for a in houses}
report={'mode':'Live editor; no manual UpdateSupport/RebuildHouse during offset phases','viewport_realtime_required':False,'terrain':{},'road':{},'restored':False}
gc.set_mobility(unreal.ComponentMobility.MOVABLE)
ground.set_actor_location(unreal.Vector(originalground.x,originalground.y,originalground.z+60),False,False)
state={'phase':0,'at':time.monotonic()}
def restore_road():
    for i,p in enumerate(originalpoints):s.set_location_at_spline_point(i,p,unreal.SplineCoordinateSpace.LOCAL,False)
    s.update_spline();road.rebuild_road()
def check_tick(dt):
    if time.monotonic()-state['at']<2.5:return
    try:
        if state['phase']==0:
            changed=[a.get_editor_property('lot_id') for a in houses if shape(a)!=baseline[a.get_path_name()] or abs(a.get_actor_location().z-baseline_z[a.get_path_name()])>.5]
            report['terrain']={'offset_cm':ground.get_actor_location().z-originalground.z,'changed_houses':changed,'house_z_deltas_cm':{a.get_editor_property('lot_id'):a.get_actor_location().z-baseline_z[a.get_path_name()] for a in houses},'passed':len(changed)==18}
            ground.set_actor_location(originalground,False,False)
            for i,p in enumerate(originalpoints):s.set_location_at_spline_point(i,unreal.Vector(p.x,p.y,p.z+80),unreal.SplineCoordinateSpace.LOCAL,False)
            s.update_spline();road.rebuild_road()
        elif state['phase']==1:
            delta=target.get_actor_location().z-z;r=target.get_actor_rotation()
            report['road']={'offset_cm':80,'house_delta_cm':delta,'pitch':r.pitch,'roll':r.roll,'passed':abs(delta-80)<.01 and abs(r.pitch)<.001 and abs(r.roll)<.001}
            restore_road()
        else:
            gc.set_mobility(originalmobility)
            report['restored']=abs(target.get_actor_location().z-z)<.01 and abs(ground.get_actor_location().z-originalground.z)<.001
            Path(unreal.Paths.project_dir()+'Saved/Mazzarino80/Historic/live_support.json').write_text(json.dumps(report,indent=2))
            unreal.unregister_slate_post_tick_callback(callback)
            unreal.log('M80_HISTORIC_LIVE_PROBE '+json.dumps(report));return
        state['phase']+=1;state['at']=time.monotonic()
    except Exception:
        ground.set_actor_location(originalground,False,False);gc.set_mobility(originalmobility);restore_road()
        unreal.unregister_slate_post_tick_callback(callback);raise
callback=unreal.register_slate_post_tick_callback(check_tick)
unreal.log('M80_HISTORIC_LIVE_PROBE_STARTED')
