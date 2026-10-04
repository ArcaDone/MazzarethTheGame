"""Fit recovered architecture uniformly; retain original blueprints and catalogue scale."""
import unreal,json
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Levels/Mazzarino80_Panoramica')
actors=editor.get_all_level_actors();plan=json.loads((ROOT/'Research/Mazzarino80/building_footprint_plan.json').read_text());by_id={r['id']:r for r in plan}
inventory=json.loads((ROOT/'Research/Mazzarino80/prepared_buildings_inventory.json').read_text())
groups={'Matrice':(['372569380','1249068308','1249068309'],['InternoChiesa02','Archipack_snap_helper_002','InternoChiesa004']),
        'ComuneCompleto':(['372573575','1249071146'],['ChurchTownHall']),
        'A_SanDomenico':(['372597222','1249054416'],['ChiesaSanDomenico'])}
proxies={a.get_editor_property('building_id'):a for a in actors if isinstance(a,unreal.MazzarinoBuilding)}
for proxy in proxies.values():
    if proxy.get_editor_property('reconstruction_status').startswith('Sostituito da '):
        proxy.set_actor_hidden_in_game(False);proxy.set_is_temporarily_hidden_in_editor(False);proxy.set_actor_enable_collision(True)
        proxy.get_editor_property('building_surface').set_visibility(True,True)
        row=by_id[proxy.get_editor_property('building_id')]
        proxy.set_editor_property('reconstruction_status','Campione stilistico: epoca e altezze da verificare' if row['pilot'] else 'Volume provvisorio')
        proxy.set_folder_path('Mazzarino80/Edifici/'+('Isolato_campione' if row['pilot'] else 'Centro_Corso/Perimetri_ripristinati'))
result=[]
for name,(ids,names) in groups.items():
    a=next(x for x in actors if x.get_actor_label()=='M80_Recuperato_'+name)
    assert 'M80_Fit_Bounds_20260928' not in [str(t) for t in a.tags],'Already fitted; preserve edits.'
    original=next(x for x in inventory if x['label']==name)
    paths={c['mesh'] for c in original['components'] if c['name'] in names}
    comps=[c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh and c.static_mesh.get_path_name() in paths]
    def bounds(components):
        values=[unreal.SystemLibrary.get_component_bounds(c) for c in components]
        mn=[min(v[0].to_tuple()[i]-v[1].to_tuple()[i] for v in values) for i in range(3)]
        mx=[max(v[0].to_tuple()[i]+v[1].to_tuple()[i] for v in values) for i in range(3)]
        return mn,mx
    mn,mx=bounds(comps);points=[p for id in ids for p in by_id[id]['ring_cm']]
    target_min=[min(p[i] for p in points) for i in range(2)];target_max=[max(p[i] for p in points) for i in range(2)]
    factor=min(1.,min((target_max[i]-target_min[i])/(mx[i]-mn[i]) for i in range(2)))
    assert .6<factor<=1,(name,factor)
    a.set_actor_scale3d(a.get_actor_scale3d()*factor);mn,mx=bounds(comps)
    target_z=min(by_id[id]['center_cm'][2] for id in ids)+30
    offset=unreal.Vector((target_min[0]+target_max[0]-mn[0]-mx[0])/2,(target_min[1]+target_max[1]-mn[1]-mx[1])/2,target_z-mn[2])
    a.set_actor_location(a.get_actor_location()+offset,False,False);a.tags=list(a.tags)+['M80_Fit_Bounds_20260928']
    replaced=set(ids)
    if name=='ComuneCompleto':
        main_path=next(c['mesh'] for c in original['components'] if c['name']=='MainComune')
        main_components=[c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh and c.static_mesh.get_path_name()==main_path]
        bmin,bmax=bounds(main_components)
        for row in plan:
            x,y,z=row['center_cm']
            if bmin[0]<x<bmax[0] and bmin[1]<y<bmax[1] and abs(z-target_z)<800:replaced.add(row['id'])
    for id in replaced:
        proxy=proxies[id];proxy.set_actor_hidden_in_game(True);proxy.set_is_temporarily_hidden_in_editor(True);proxy.set_actor_enable_collision(False)
        proxy.get_editor_property('building_surface').set_visibility(False,True);proxy.set_editor_property('reconstruction_status','Sostituito da '+name)
        proxy.set_folder_path('Mazzarino80/Edifici/Perimetri_sostituiti')
    result.append({'name':name,'uniform_scale_factor':factor,'scale':list(a.get_actor_scale3d().to_tuple()),'location_cm':list(a.get_actor_location().to_tuple()),'replacement_ids':sorted(replaced),'fit':'Bounding boxes of mapped architecture; entrances and terrain still require visual review'})
assert unreal.EditorLevelLibrary.save_current_level()
(ROOT/'Saved/Mazzarino80/restored_buildings_fit.json').write_text(json.dumps(result,indent=2))
unreal.log('M80_RESTORED_FIT_DONE '+json.dumps(result))
