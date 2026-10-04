"""First editable building phase. Does not load or modify MazzarethMap."""
import unreal,json,math
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample');DATA=ROOT/'Research/Mazzarino80'
LEVEL='/Game/Levels/Mazzarino80_Panoramica'
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert levels.load_level(LEVEL)
existing=actors.get_all_level_actors()
assert not any(isinstance(a,unreal.MazzarinoBuilding) for a in existing),'Phase already installed: do not recreate user edits.'
plan=json.loads((DATA/'building_footprint_plan.json').read_text())
inventory=json.loads((DATA/'prepared_buildings_inventory.json').read_text())
renames=json.loads((DATA/'comune_building_asset_renames.json').read_text())
assets=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
def material(name,color,roughness=.85):
    path='/Game/Mazzarino80/Buildings/Materials';m=unreal.load_asset(path+'/'+name)
    if m:return m
    m=assets.create_asset(name,path,unreal.Material,unreal.MaterialFactoryNew())
    c=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-300,0)
    c.set_editor_property('constant',unreal.LinearColor(*color,1))
    lib.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
    r=lib.create_material_expression(m,unreal.MaterialExpressionConstant,-300,120);r.set_editor_property('r',roughness)
    lib.connect_material_property(r,'',unreal.MaterialProperty.MP_ROUGHNESS);lib.recompile_material(m)
    assert unreal.EditorAssetLibrary.save_loaded_asset(m);return m
neutral=material('M80_Intonaco_Provvisorio',(.43,.39,.31))
roof_neutral=material('M80_Tetto_Provvisorio',(.18,.13,.09))
glass=material('M80_Vetri_Scuri',(.012,.020,.022),.3)
load=lambda p:unreal.load_asset(renames[p])
facades=[load(p) for p in renames if p.endswith(('MI_Stucco_01','MI_Stucco_02','MI_Stucco_03','MI_StuccoPainted_02','MI_Stucco_Facade_wfnjdgl_2K','MI_Roman_Stone_Wall_tf2kaa2n_4K'))]
roof=load('/Game/Megascans/Surfaces/Red_Roof_Tiles_tfqnfggs/MI_Red_Roof_Tiles_tfqnfggs_4K')
window=load('/Game/SoulCity/Environment/Meshes/Building_Slum/SM_Slums_Window_01a')
door=load('/Game/OldWestAssets/OldWestVol6/VOL6/Meshes/SM_Door_06c')
assert len(facades)>=4 and all(facades) and roof and window and door
created={};errors=[];pilot=[]
with unreal.ScopedSlowTask(len(plan),'Creo i perimetri modificabili degli edifici') as progress:
    progress.make_dialog(True)
    for index,row in enumerate(plan):
        center=row['center_cm'];a=actors.spawn_actor_from_class(unreal.MazzarinoBuilding,unreal.Vector(*center))
        a.set_actor_label('M80_Edificio_'+row['id']);a.set_editor_property('building_id',row['id'])
        zone='Centro_Corso' if 35000<center[0]<115000 and -18000<center[1]<26000 else 'Altri_quartieri'
        tile=f"Settore_{int(center[0]//15000):02d}_{int(center[1]//15000):02d}"
        a.set_folder_path('Mazzarino80/Edifici/'+('Isolato_campione' if row['pilot'] else zone+'/'+tile))
        a.tags=['M80_EditableBuilding','OSM_'+row['id'],'Epoca_da_verificare']
        p=a.get_editor_property('footprint');p.clear_spline_points(False)
        for x,y in row['ring_cm']:p.add_spline_point(unreal.Vector(x-center[0],y-center[1],0),unreal.SplineCoordinateSpace.LOCAL,False)
        p.set_closed_loop(True,False)
        for j in range(p.get_number_of_spline_points()):p.set_spline_point_type(j,unreal.SplinePointType.LINEAR,False)
        p.update_spline()
        floors=max(1,round(row['height_m']/3.2));a.set_editor_property('floor_count',floors)
        a.set_editor_property('floor_height_meters',row['height_m']/floors)
        a.set_editor_property('facade_material',neutral);a.set_editor_property('roof_material',roof_neutral)
        if row['pilot']:
            a.set_editor_property('reconstruction_status','Campione stilistico: epoca e altezze da verificare')
            a.set_editor_property('facade_material',facades[len(pilot)%len(facades)])
            a.set_editor_property('roof_material',roof)
            a.set_editor_property('roof_rise_meters',.85 if row['area_m2']<250 else 1.25)
            a.set_editor_property('roof_ridge_angle_degrees',row['ridge_degrees'])
            a.set_editor_property('detailed_facade',True);a.set_editor_property('front_edge_index',row['front_edge'])
            a.set_editor_property('window_mesh',window);a.set_editor_property('door_mesh',door)
            a.set_editor_property('window_backing_material',glass);pilot.append(row['id'])
        a.rebuild_building()
        error=a.get_editor_property('geometry_error')
        if error:errors.append({'id':row['id'],'error':error})
        created[row['id']]=a
        if index%100==0:unreal.log('M80_BUILDINGS_PROGRESS '+str(index))
        progress.enter_progress_frame(1)
# Abort before disabling the original combined mesh if any imported footprint needs repair.
assert not errors,json.dumps(errors)
for a in existing:
    if a.get_actor_label()=='M80_Edifici':
        a.set_actor_hidden_in_game(True);a.set_is_temporarily_hidden_in_editor(True);a.set_actor_enable_collision(False)
        c=a.get_component_by_class(unreal.StaticMeshComponent);c.set_visibility(False,True)
        a.set_folder_path('Mazzarino80/Riferimenti_disattivati');a.tags=['M80_PreviousCombinedBuildings']

# The municipal model includes the Carmine church. Use that identifiable footprint as anchor.
placements={'ComuneCompleto':('372573575','ChurchTownHall'),'Matrice':('372569380','InternoChiesa02'),'A_SanDomenico':('372597222','ChiesaSanDomenico')}
placed=[]
for item in inventory:
    if item['label'] not in placements:continue
    target_id,component_name=placements[item['label']];row=next(r for r in plan if r['id']==target_id)
    source_primary=next(c for c in item['components'] if c['name']==component_name)
    tr=item['transform'];p=tr['translation'];rotation=tr['rotation']
    cls=unreal.load_class(None,item['class']);assert cls,item['class']
    # Global Y reflection matches the corrected map and preserves the assembled relative placement.
    model=actors.spawn_actor_from_class(cls,unreal.Vector(p[0],-p[1],p[2]),unreal.Rotator(pitch=rotation[0],yaw=-rotation[1],roll=-rotation[2]))
    model.set_actor_scale3d(unreal.Vector(tr['scale'][0],-tr['scale'][1],tr['scale'][2]))
    model.set_actor_label('M80_Recuperato_'+item['label']);model.set_folder_path('Mazzarino80/Edifici/Strutture_recuperate')
    primary=next(c for c in model.get_components_by_class(unreal.StaticMeshComponent) if c.get_name().split('_GEN_VARIABLE')[0]==component_name or c.static_mesh and c.static_mesh.get_path_name()==source_primary['mesh'])
    center,extent,_=unreal.SystemLibrary.get_component_bounds(primary)
    # Preserve model scale; register its centre on the mapped church. Model bases can differ from render bounds.
    target=row['center_cm'];bottom=center.z-extent.z
    offset=unreal.Vector(target[0]-center.x,target[1]-center.y,target[2]+30-bottom)
    model.set_actor_location(model.get_actor_location()+offset,False,False)
    model.tags=['M80_RestoredBuilding','M80_AlignmentReview','OSM_'+target_id]
    # Hide only mapped polygons whose centres lie within the recovered architectural bounds.
    center,extent,_=unreal.SystemLibrary.get_component_bounds(primary)
    replaced=[]
    for r in plan:
        inside=abs(r['center_cm'][0]-center.x)<extent.x and abs(r['center_cm'][1]-center.y)<extent.y
        if r['id']==target_id or (inside and abs(r['center_cm'][2]-target[2])<900):
            proxy=created[r['id']];proxy.set_actor_hidden_in_game(True);proxy.set_is_temporarily_hidden_in_editor(True)
            proxy.get_editor_property('building_surface').set_visibility(False,True);proxy.set_actor_enable_collision(False)
            proxy.set_editor_property('reconstruction_status','Sostituito da '+item['label']);proxy.set_folder_path('Mazzarino80/Edifici/Perimetri_sostituiti')
            replaced.append(r['id'])
    placed.append({'label':item['label'],'anchor_osm':target_id,'location':list(model.get_actor_location().to_tuple()),'rotation':-rotation[1],'scale':list(model.get_actor_scale3d().to_tuple()),'replaced':replaced,'status':'Prima posa; verificare fronti, quota e piazze'})
assert unreal.EditorLevelLibrary.save_current_level()
result={'level':LEVEL,'editable_buildings':len(created),'pilot_ids':pilot,'restored':placed,'errors':errors,'historical_status':'Perimetri attuali OSM; piani e stile indicativi, non verificati al 1980'}
(ROOT/'Saved/Mazzarino80/buildings_phase_result.json').write_text(json.dumps(result,indent=2))
unreal.log('M80_BUILDING_PHASE_DONE '+json.dumps(result))
