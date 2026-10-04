"""Upgrade existing actors in place; retain current footprints and landmark edits."""
import unreal,json,math,hashlib
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
PLAN={r['id']:r for r in json.loads((ROOT/'Research/Mazzarino80/building_footprint_plan.json').read_text())}
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert levels.load_level('/Game/Levels/Mazzarino80_Panoramica')
assets=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
PATH='/Game/Mazzarino80/Buildings/Materials'
LIB='/Game/Mazzarino80/Library/Comune'
def material(name,color,texture=None,normal=None,rough=.85,metal=0):
    m=unreal.load_asset(PATH+'/'+name)
    if m and not texture:return m
    if m:lib.delete_all_material_expressions(m)
    else:m=assets.create_asset(name,PATH,unreal.Material,unreal.MaterialFactoryNew())
    m.set_editor_property('used_with_instanced_static_meshes',True)
    tint=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-600,0)
    tint.set_editor_property('constant',unreal.LinearColor(*color,1))
    output=tint
    if texture:
        sample=lib.create_material_expression(m,unreal.MaterialExpressionTextureSample,-800,200)
        sample.set_editor_property('texture',unreal.load_asset(texture))
        sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if unreal.load_asset(texture).get_editor_property('virtual_texture_streaming') else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        multiply=lib.create_material_expression(m,unreal.MaterialExpressionMultiply,-350,0)
        lib.connect_material_expressions(sample,'RGB',multiply,'A');lib.connect_material_expressions(tint,'',multiply,'B');output=multiply
    lib.connect_material_property(output,'',unreal.MaterialProperty.MP_BASE_COLOR)
    if normal:
        n=lib.create_material_expression(m,unreal.MaterialExpressionTextureSample,-600,400)
        n.set_editor_property('texture',unreal.load_asset(normal));n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if unreal.load_asset(normal).get_editor_property('virtual_texture_streaming') else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        lib.connect_material_property(n,'RGB',unreal.MaterialProperty.MP_NORMAL)
    for prop,value,y in [(unreal.MaterialProperty.MP_ROUGHNESS,rough,500),(unreal.MaterialProperty.MP_METALLIC,metal,650)]:
        n=lib.create_material_expression(m,unreal.MaterialExpressionConstant,-300,y);n.set_editor_property('r',value);lib.connect_material_property(n,'',prop)
    lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m);return m
stucco=LIB+'/Megascans/Surfaces/Stucco_Facade_wfnjdgl/T_Stucco_Facade_wfnjdgl_2K_'
colors=[(.94,.83,.65),(.74,.68,.56),(.88,.74,.56),(.69,.72,.67),(.78,.58,.42),(.93,.90,.80)]
facades=[material('M80_Intonaco_Rilievo_'+str(i),c,stucco+'D',stucco+'N') for i,c in enumerate(colors)]
stone=LIB+'/Megascans/Surfaces/Roman_Stone_Wall_tf2kaa2n/T_Roman_Stone_Wall_tf2kaa2n_4K_'
stone_mat=material('M80_Pietra_Facciata',(.85,.80,.67),stone+'D',stone+'N')
roofsource=LIB+'/Megascans/Surfaces/Red_Roof_Tiles_tfqnfggs/T_Red_Roof_Tiles_tfqnfggs_4K_'
roof=material('M80_Coppi_Rilievo',(.85,.73,.60),roofsource+'D',roofsource+'N')
terrace=material('M80_Pavimento_Terrazza',(.38,.32,.25))
trim=material('M80_Cornici_Pietra',(.57,.49,.36),stone+'D',stone+'N')
metal=material('M80_Ferro_Brunito',(.035,.042,.039),rough=.54,metal=.65)
shutters=[material('M80_Persiane_'+str(i),c,rough=.65) for i,c in enumerate([(.075,.13,.105),(.17,.12,.07),(.15,.19,.20)])]
glass=unreal.load_asset(PATH+'/M80_Vetri_Scuri')
window=unreal.load_asset(LIB+'/SoulCity/Environment/Meshes/Building_Slum/SM_Slums_Window_01a')
door=unreal.load_asset(LIB+'/OldWestAssets/OldWestVol6/VOL6/Meshes/SM_Door_06c')
assert all(facades) and roof and trim and metal and glass and window and door
def footprint(a):
    p=a.get_editor_property('footprint')
    return [list(p.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD).to_tuple()) for i in range(p.get_number_of_spline_points())]
report={'detailed':[],'skyline_count':0,'errors':[],'footprint_changes':[],'landmarks_preserved':[], 'reference':'User Street View screenshot: 222 Corso Vittorio Emanuele II, June 2025; architectural treatment provisional for 1980.'}
allactors=editor.get_all_level_actors()
for a in allactors:
    if a.get_actor_label().startswith('M80_Recuperato_'):
        report['landmarks_preserved'].append({'label':a.get_actor_label(),'location':list(a.get_actor_location().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple())})
for a in allactors:
    if not isinstance(a,unreal.MazzarinoBuilding):continue
    key=a.get_editor_property('building_id');row=PLAN.get(key)
    if not row or str(a.get_editor_property('reconstruction_status')).startswith('Sostituito'):continue
    before=footprint(a);seed=int(key)%1009
    detailed=row['distance_corso_m']<60 and 35000<row['center_cm'][0]<112000 and 20<row['area_m2']<3000
    tags=row.get('tags',{});church=tags.get('building') in ('church','cathedral','chapel') or tags.get('amenity')=='place_of_worship'
    a.set_editor_property('composition_seed',seed)
    a.set_editor_property('facade_section_width_meters',7.5+(seed%4))
    a.set_editor_property('height_variation_meters',0 if church or row['area_m2']<50 else (.45+.22*(seed%4)))
    pitched=not church and row['area_m2']<850 and seed%5<3
    a.set_editor_property('roof_rise_meters',(.9+.25*(seed%4)) if pitched else 0)
    a.set_editor_property('roof_ridge_angle_degrees',row['ridge_degrees'])
    a.set_editor_property('roof_material',roof if pitched else terrace)
    a.set_editor_property('facade_material',stone_mat if seed%9==0 else facades[seed%len(facades)])
    a.set_editor_property('detailed_facade',detailed)
    if detailed:
        a.set_editor_property('front_edge_index',row['front_edge'])
        a.set_editor_property('detail_side_facades',abs(row['center_cm'][0]-80000)<7000 and abs(row['center_cm'][1]-8000)<8000)
        a.set_editor_property('window_mesh',window);a.set_editor_property('door_mesh',door);a.set_editor_property('window_backing_material',glass)
        a.set_editor_property('trim_material',trim);a.set_editor_property('metal_material',metal);a.set_editor_property('shutter_material',shutters[seed%3])
        a.set_editor_property('balcony_style',2 if row['area_m2']>400 and seed%3!=0 else 1)
        a.set_editor_property('balcony_depth_meters',.75+.1*(seed%3))
        a.set_editor_property('add_shutters',seed%4!=0)
        a.set_editor_property('roof_terrace',not pitched and row['area_m2']>100 and seed%2==0)
        a.set_editor_property('window_width_meters',.9+.1*(seed%3));a.set_editor_property('window_spacing_meters',2.8+.2*(seed%3))
        a.set_editor_property('reconstruction_status','Prospetto articolato: balconi e coperture indicativi, epoca da verificare')
        # The front opposite the Matrice in the supplied view has ground + three upper levels.
        if key=='1249069246':
            a.set_editor_property('floor_count',4);a.set_editor_property('floor_height_meters',3.05)
            a.set_editor_property('balcony_style',2);a.set_editor_property('roof_rise_meters',0);a.set_editor_property('roof_material',terrace);a.set_editor_property('roof_terrace',True)
    a.rebuild_building()
    if a.get_editor_property('geometry_error'):report['errors'].append({'id':key,'error':a.get_editor_property('geometry_error')})
    if footprint(a)!=before:report['footprint_changes'].append(key)
    report['skyline_count']+=1
    if detailed:
        report['detailed'].append({'id':key,'windows':a.get_editor_property('windows').get_instance_count(),'doors':a.get_editor_property('doors').get_instance_count(),'masonry':a.get_editor_property('masonry_details').get_instance_count(),'railings':a.get_editor_property('metal_details').get_instance_count(),'shutters':a.get_editor_property('shutters').get_instance_count(),'roof_rise':a.get_editor_property('roof_rise_meters'),'terrace':a.get_editor_property('roof_terrace')})
assert not report['errors'] and not report['footprint_changes'],json.dumps(report)
# A reproducible comparison camera; landmark transforms remain exactly as saved by the user.
audit=json.loads((ROOT/'Saved/Mazzarino80/current_view_audit.json').read_text())
location=audit['camera'][0];r=audit['camera'][1]
cam=next((a for a in allactors if a.get_actor_label()=='M80_Camera_Confronto_90'),None)
if not cam:cam=editor.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(*location))
cam.set_actor_label('M80_Camera_Confronto_90');cam.set_folder_path('Mazzarino80/Verifiche')
cam.set_actor_location(unreal.Vector(*location),False,False)
cam.set_actor_rotation(unreal.Rotator(pitch=r[1],yaw=r[2],roll=0),False)
cam.camera_component.set_field_of_view(90);cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
assert unreal.EditorLevelLibrary.save_current_level()
(ROOT/'Saved/Mazzarino80/facade_variety_report.json').write_text(json.dumps(report,indent=2))
unreal.log('M80_FACADE_VARIETY_DONE '+str(len(report['detailed']))+' facades / '+str(report['skyline_count'])+' roofs')
