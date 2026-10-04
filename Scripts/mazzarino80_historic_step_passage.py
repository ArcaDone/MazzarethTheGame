"""Check lateral clearance beside the two Catania entrance-step contacts."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir())
e=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert w.get_name()=='Mazzarino80_CaseStoriche_Campione'
actors=e.get_all_level_actors()
buildings=[a for a in actors if isinstance(a,(unreal.MazzarinoHistoricBuilding,unreal.MazzarinoBuilding)) or a.get_actor_label().startswith('M80_Recuperato_')]
report=json.loads((root/'Saved/Mazzarino80/Historic/routes.json').read_text())
checks=[]
for row in report['roads']:
    road=next(a for a in actors if a.get_actor_label()==row['label'])
    spline=road.get_editor_property('spline')
    for contact in row['collisions']:
        if not (contact['actor'] or '').startswith('M80_Storica_'):continue
        tests=[]
        for offset in [-55.,-35.,-15.,15.,35.,55.]:
            centers=[]
            for distance in [contact['s']-160,contact['s']-80,contact['s'],contact['s']+80]:
                p=spline.get_location_at_distance_along_spline(distance,unreal.SplineCoordinateSpace.WORLD)
                t=spline.get_direction_at_distance_along_spline(distance,unreal.SplineCoordinateSpace.WORLD)
                p=p+unreal.Vector(-t.y*offset,t.x*offset,0)
                hit=unreal.SystemLibrary.line_trace_single(w,p+unreal.Vector(0,0,3000),p-unreal.Vector(0,0,1000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,buildings,unreal.DrawDebugTrace.NONE,True)
                h=hit.to_tuple() if hit else None
                if not h or not h[0]:break
                centers.append(h[4]+unreal.Vector(0,0,94))
            hits=[]
            for a,b in zip(centers,centers[1:]):
                hit=unreal.SystemLibrary.capsule_trace_single(w,a,b,34,88,unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],unreal.DrawDebugTrace.NONE,True)
                h=hit.to_tuple() if hit else None
                if h and h[0]:hits.append({'actor':h[9].get_actor_label() if h[9] else None,'normal':list(h[6].to_tuple())})
            tests.append({'offset_cm':offset,'complete':len(centers)==4,'hits':hits,'clear':len(centers)==4 and not hits})
        checks.append({'road':row['label'],'contact':contact,'alternatives':tests,'passage_found':any(t['clear'] for t in tests)})
(root/'Saved/Mazzarino80/Historic/step_passage.json').write_text(json.dumps(checks,indent=2))
unreal.log('M80_STEP_PASSAGES '+json.dumps([{'road':c['road'],'clear':c['passage_found']} for c in checks]))

