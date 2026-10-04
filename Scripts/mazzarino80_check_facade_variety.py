import unreal,json,math,struct
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert levels.load_level('/Game/Levels/Mazzarino80_Panoramica')
report=json.loads((ROOT/'Saved/Mazzarino80/facade_variety_report.json').read_text())
audit=json.loads((ROOT/'Saved/Mazzarino80/current_view_audit.json').read_text())
allactors=editor.get_all_level_actors();buildings=[a for a in allactors if isinstance(a,unreal.MazzarinoBuilding)]
roads=[a for a in allactors if isinstance(a,unreal.MazzarinoRoadSpline)]
errors=[];detail=[];landmarks=[];degenerate=[];triangles=0;roof_hits=[]
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for a in buildings:
    if a.get_editor_property('geometry_error'):errors.append(a.get_actor_label())
    if not str(a.get_editor_property('reconstruction_status')).startswith('Sostituito'):
        surface=a.get_editor_property('building_surface')
        for section in range(surface.get_num_sections()):
            vertices,indices,normals,uv,tangents=unreal.ProceduralMeshLibrary.get_section_from_procedural_mesh(surface,section)
            packed=[struct.pack('fff',v.x,v.y,v.z) for v in vertices]
            for i in range(0,len(indices),3):
                triangles+=1
                if len({packed[indices[i]],packed[indices[i+1]],packed[indices[i+2]]})<3:degenerate.append([a.get_editor_property('building_id'),section,i//3])
    if not a.get_editor_property('detailed_facade') or str(a.get_editor_property('reconstruction_status')).startswith('Sostituito'):continue
    key=a.get_editor_property('building_id');parts={k:a.get_editor_property(k).get_instance_count() for k in ('windows','doors','masonry_details','metal_details','shutters')}
    assert parts['windows'] and parts['masonry_details'],(key,parts)
    surface=a.get_editor_property('building_surface');assert surface.get_num_sections()>=2
    detail.append({'id':key,**parts,'collision':str(surface.get_collision_enabled())})
    if key in ('1249069246','1249068307','1249069205','1249082264'):
        v,t,n,u,g=unreal.ProceduralMeshLibrary.get_section_from_procedural_mesh(surface,1)
        q=(v[t[0]]+v[t[1]]+v[t[2]])/3+a.get_actor_location()
        hit=unreal.SystemLibrary.line_trace_single(world,q+unreal.Vector(0,0,10),q-unreal.Vector(0,0,10),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[],unreal.DrawDebugTrace.NONE,True).to_tuple()
        roof_hits.append({'id':key,'hit_expected':hit[0] and hit[9]==a})
for old in audit['landmarks']:
    a=next(a for a in allactors if a.get_actor_label()==old['label'])
    assert list(a.get_actor_location().to_tuple())==old['location']
    assert list(a.get_actor_scale3d().to_tuple())==old['scale']
    landmarks.append(a.get_actor_label())
assert len(buildings)==3216 and len(roads)==1016 and not errors and not degenerate,(errors,degenerate[:20])
assert roof_hits and all(h['hit_expected'] for h in roof_hits),roof_hits
# Verify editing an existing spline point actually updates the wall, then restore it without saving.
a=next(a for a in buildings if a.get_editor_property('building_id')=='1249069246')
p=a.get_editor_property('footprint');old=p.get_location_at_spline_point(0,unreal.SplineCoordinateSpace.LOCAL)
p.set_location_at_spline_point(0,old+unreal.Vector(30,0,0),unreal.SplineCoordinateSpace.LOCAL,True);a.rebuild_building()
assert not a.get_editor_property('geometry_error')
p.set_location_at_spline_point(0,old,unreal.SplineCoordinateSpace.LOCAL,True);a.rebuild_building()
assert p.get_location_at_spline_point(0,unreal.SplineCoordinateSpace.LOCAL)==old
out={'buildings':len(buildings),'roads':len(roads),'detailed':len(detail),'landmarks_preserved':landmarks,'errors':errors,'triangles_checked':triangles,'degenerate_triangles':len(degenerate),'roof_collision_samples':roof_hits,'spline_edit_and_restore':True,'parts':detail}
(ROOT/'Saved/Mazzarino80/facade_variety_validation.json').write_text(json.dumps(out,indent=2))
unreal.log('M80_FACADE_VARIETY_VALIDATED '+str(len(detail)))
