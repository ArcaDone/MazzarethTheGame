import unreal,json
from pathlib import Path
e=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
houses=[a for a in e.get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding)]
g=houses[0].get_editor_property('ground_actor');c=g.get_component_by_class(unreal.StaticMeshComponent)
report={'ground':g.get_path_name(),'collision':str(c.get_collision_enabled()),'profile':str(c.get_collision_profile_name()),'mesh':c.static_mesh.get_path_name(),'samples':[]}
for a in houses[:6]:
    p=a.get_actor_location();start=unreal.Vector(p.x,p.y,p.z+10000);end=unreal.Vector(p.x,p.y,p.z-10000)
    row={'house':a.get_actor_label()}
    for complex_trace in [False,True]:
        hit=c.line_trace_component(start,end,complex_trace,False,False)
        row['component_'+str(complex_trace)]=str(hit)
        hits=unreal.SystemLibrary.line_trace_multi(w,start,end,unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,complex_trace,houses,unreal.DrawDebugTrace.NONE,True)
        row['world_'+str(complex_trace)]=[[h.to_tuple()[9].get_actor_label() if h.to_tuple()[9] else None,list(h.to_tuple()[4].to_tuple())] for h in hits]
    report['samples'].append(row)
Path(unreal.Paths.project_dir()+'Saved/Mazzarino80/Historic/support_audit.json').write_text(json.dumps(report,indent=2))
unreal.log('HISTORIC_SUPPORT_AUDIT '+json.dumps(report))
