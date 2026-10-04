"""Audit walking corridors with a player-sized capsule, including buildings.
This is an editor collision audit, not a claim of a completed Play walkthrough.
"""
import unreal,json,math
from pathlib import Path
root=Path(unreal.Paths.project_dir());out=root/'Saved/Mazzarino80/Historic'
e=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert w.get_name()=='Mazzarino80_CaseStoriche_Campione'
actors=e.get_all_level_actors();houses=[a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)]
buildings=[a for a in actors if isinstance(a,(unreal.MazzarinoHistoricBuilding,unreal.MazzarinoBuilding)) or a.get_actor_label().startswith('M80_Recuperato_')]
roads={a.get_editor_property('entrance_road') for a in houses}
def vec(v):return list(v.to_tuple())
report={'mode':'Editor capsule sweep: radius 34 cm, half height 88 cm; buildings included','region_cm':[72000,83500,7500,15000],'roads':[]}
for road in sorted(roads,key=lambda a:a.get_actor_label()):
    s=road.get_editor_property('spline');length=s.get_spline_length();n=max(2,math.ceil(length/80.))
    points=[];collisions=[];last=None
    for i in range(n+1):
        p=s.get_location_at_distance_along_spline(length*i/n,unreal.SplineCoordinateSpace.WORLD)
        if not (72000<p.x<83500 and 7500<p.y<15000):last=None;continue
        result=unreal.SystemLibrary.line_trace_single(w,p+unreal.Vector(0,0,3000),p-unreal.Vector(0,0,1000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,buildings,unreal.DrawDebugTrace.NONE,True)
        if result is None:points.append({'s':length*i/n,'xy':vec(p)[:2],'ground':None});last=None;continue
        hit=result.to_tuple()
        if not hit[0]:points.append({'s':length*i/n,'xy':vec(p)[:2],'ground':None});last=None;continue
        top=hit[4];center=top+unreal.Vector(0,0,94)
        row={'s':length*i/n,'position':vec(top),'ground':hit[9].get_actor_label() if hit[9] else None}
        if last:
            sweepresult=unreal.SystemLibrary.capsule_trace_single(w,last,center,34,88,unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],unreal.DrawDebugTrace.NONE,True)
            sweep=sweepresult.to_tuple() if sweepresult else None
            row['blocked']=bool(sweep and sweep[0]);row['rise_cm']=center.z-last.z
            if sweep and sweep[0]:
                collision={'s':length*i/n,'actor':sweep[9].get_actor_label() if sweep[9] else None,'component':sweep[10].get_name() if sweep[10] else None,'normal':vec(sweep[6]),'position':vec(sweep[5])};collisions.append(collision)
        points.append(row);last=center
    if points:
        report['roads'].append({'label':road.get_actor_label(),'width_m':road.get_editor_property('width_meters'),'points':points,'collisions':collisions,'control_points':[vec(s.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD)) for i in range(s.get_number_of_spline_points())]})
(out/'routes.json').write_text(json.dumps(report,indent=2))
unreal.log('M80_HISTORIC_ROUTES '+json.dumps([{'road':r['label'],'points':len(r['points']),'blocked':len(r['collisions'])} for r in report['roads']]))
