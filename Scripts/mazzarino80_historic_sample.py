"""Create the 18-house study in an independent map; retain all original XY lots.
Run with Unreal 5.5 Python after installing the historic-house plugin.
"""
import unreal, json, math, hashlib
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())
OUT=ROOT/'Saved/Mazzarino80/Historic'
OUT.mkdir(parents=True,exist_ok=True)
SOURCE='/Game/Levels/Mazzarino80_Panoramica'
TARGET='/Game/Levels/Mazzarino80_CaseStoriche_Campione'
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not unreal.EditorAssetLibrary.does_asset_exist(TARGET):
    assert unreal.EditorAssetLibrary.duplicate_asset(SOURCE,TARGET), 'Cannot duplicate map'
assert levels.load_level(TARGET)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name()=='Mazzarino80_CaseStoriche_Campione'
actors=editor.get_all_level_actors()
assert not any(isinstance(a,unreal.MazzarinoHistoricBuilding) for a in actors),'Sample already generated'
plan={r['id']:r for r in json.loads((ROOT/'Research/Mazzarino80/building_footprint_plan.json').read_text())}
old={a.get_editor_property('building_id'):a for a in actors if isinstance(a,unreal.MazzarinoBuilding)}
roads=[a for a in actors if isinstance(a,unreal.MazzarinoRoadSpline)]
ground=next(a for a in actors if a.get_actor_label()=='M80_Terreno')
def landmark(a):return {'label':a.get_actor_label(),'location':list(a.get_actor_location().to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple())}
landmarks=[landmark(a) for a in actors if a.get_actor_label().startswith('M80_Recuperato_')]

PATH='/Game/Mazzarino80/Historic/Materials'
assets=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
LIB='/Game/Mazzarino80/Library/Comune'
def material(name,color,texture=None,normal=None,rough=.9,metal=0):
    m=unreal.load_asset(PATH+'/'+name)
    if m:return m
    m=assets.create_asset(name,PATH,unreal.Material,unreal.MaterialFactoryNew())
    m.set_editor_property('used_with_instanced_static_meshes',True)
    tint=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-500,0)
    tint.set_editor_property('constant',unreal.LinearColor(*color,1));output=tint
    if texture:
        tex=unreal.load_asset(texture);assert tex,texture
        sample=lib.create_material_expression(m,unreal.MaterialExpressionTextureSample,-700,200)
        sample.set_editor_property('texture',tex)
        sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if tex.get_editor_property('virtual_texture_streaming') else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        mul=lib.create_material_expression(m,unreal.MaterialExpressionMultiply,-250,0)
        lib.connect_material_expressions(sample,'RGB',mul,'A');lib.connect_material_expressions(tint,'',mul,'B');output=mul
    lib.connect_material_property(output,'',unreal.MaterialProperty.MP_BASE_COLOR)
    if normal:
        tex=unreal.load_asset(normal);assert tex,normal
        n=lib.create_material_expression(m,unreal.MaterialExpressionTextureSample,-600,400);n.set_editor_property('texture',tex)
        n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if tex.get_editor_property('virtual_texture_streaming') else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        lib.connect_material_property(n,'RGB',unreal.MaterialProperty.MP_NORMAL)
    for prop,value,y in [(unreal.MaterialProperty.MP_ROUGHNESS,rough,500),(unreal.MaterialProperty.MP_METALLIC,metal,650)]:
        n=lib.create_material_expression(m,unreal.MaterialExpressionConstant,-300,y);n.set_editor_property('r',value);lib.connect_material_property(n,'',prop)
    lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m);return m
stucco=LIB+'/Megascans/Surfaces/Stucco_Facade_wfnjdgl/T_Stucco_Facade_wfnjdgl_2K_'
stone=LIB+'/Megascans/Surfaces/Roman_Stone_Wall_tf2kaa2n/T_Roman_Stone_Wall_tf2kaa2n_4K_'
roof=LIB+'/Megascans/Surfaces/Red_Roof_Tiles_tfqnfggs/T_Red_Roof_Tiles_tfqnfggs_4K_'
palette=[(.58,.51,.40),(.69,.62,.49),(.46,.43,.36),(.63,.48,.34),(.72,.69,.59),(.48,.44,.36)]
plasters=[material('M80_Calce_consumata_'+str(i),c,stucco+'D',stucco+'N') for i,c in enumerate(palette)]
mats={'stone_material':material('M80_Pietra_modesta',(.60,.58,.49),stone+'D',stone+'N'),
      'roof_material':material('M80_Coppi_vecchi',(.60,.49,.36),roof+'D',roof+'N'),
      'terrace_material':material('M80_Terrazza_calce',(.34,.31,.26),stucco+'D',stucco+'N'),
      'iron_material':material('M80_Ferro_ossidato',(.065,.055,.042),rough=.8,metal=.55),
      'glass_material':material('M80_Vetro_ombra',(.028,.04,.034),rough=.5),
      'damp_material':material('M80_Umidita',(.18,.17,.125),stucco+'D',stucco+'N'),
      'repair_material':material('M80_Rappezzo',(.38,.35,.29),stucco+'D',stucco+'N'),
      'cloth_material':material('M80_Tessuto_sbiadito',(.30,.40,.33),stucco+'D'),
      'gray_material':material('M80_Grigio_forme',(.40,.40,.40))}
woods=[material('M80_Legno_persiane_'+str(i),c,stucco+'D',stucco+'N') for i,c in enumerate([(.10,.16,.12),(.24,.17,.10),(.21,.23,.22)])]
EF=unreal.M80HouseFamily
selection=[('1249069275',EF.POPULAR),('1249069286',EF.POPULAR),('1249069247',EF.POPULAR),
           ('1249069213',EF.NARROW),('1249069271',EF.NARROW),('1249069276',EF.NARROW),
           ('1249069204',EF.CORNER),('1249069237',EF.CORNER),('1249069219',EF.CORNER),
           ('1249069205',EF.COURTYARD),('1249069228',EF.COURTYARD),('1249069202',EF.COURTYARD),
           ('1249069200',EF.EXTENDED),('1249069235',EF.EXTENDED),('1249069287',EF.EXTENDED),
           ('1249068307',EF.PALAZZETTO),('1249069246',EF.PALAZZETTO),('1249069229',EF.PALAZZETTO)]
def vec(v):return [v.x,v.y,v.z]
def ring(a):
    p=a.get_editor_property('footprint');return [vec(p.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD)) for i in range(p.get_number_of_spline_points())]
allrings={k:ring(a) for k,a in old.items()}
def edge_dist(q,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/max(1,dx*dx+dy*dy)));return math.hypot(q[0]-a[0]-t*dx,q[1]-a[1]-t*dy)
def parties(key,points):
    result=[]
    for i,a in enumerate(points):
        b=points[(i+1)%len(points)];length=math.dist(a[:2],b[:2]);mid=[(a[j]+b[j])*.5 for j in range(2)]
        if length<80:continue
        for other,poly in allrings.items():
            if other==key:continue
            if min(math.dist(mid,q[:2]) for q in poly)>10000:continue
            hit=False
            for j,c in enumerate(poly):
                d=poly[(j+1)%len(poly)]
                if edge_dist(mid,c,d)<30 and edge_dist([a[0]*.25+b[0]*.75,a[1]*.25+b[1]*.75],c,d)<35 and edge_dist([a[0]*.75+b[0]*.25,a[1]*.75+b[1]*.25],c,d)<35:hit=True;break
            if hit:result.append(i);break
    return result

report={'map':TARGET,'reference':'User images 3/4 details; image 5 modest lived-in prewar homes. Architectural study, not certified historical reconstruction.', 'houses':[], 'landmarks_before':landmarks,'baseline_camera':{},'errors':[]}
for cam in actors:
    if isinstance(cam,unreal.CameraActor):report['baseline_camera'][cam.get_actor_label()]={'location':vec(cam.get_actor_location()),'rotation':list(cam.get_actor_rotation().to_tuple()),'fov':cam.camera_component.field_of_view}
for index,(key,family) in enumerate(selection):
    source=old[key];points=allrings[key];location=source.get_actor_location()
    a=editor.spawn_actor_from_class(unreal.MazzarinoHistoricBuilding,location)
    a.set_actor_label(f'M80_Storica_{family.name}_{key}');a.set_folder_path('Mazzarino80/Campione_case_storiche/'+family.name)
    for prop,val in mats.items():a.set_editor_property(prop,val)
    a.set_editor_property('family',family);a.set_editor_property('lot_id',key);a.set_editor_property('seed',1980+index*137)
    party=parties(key,points)
    # Old fronts were selected relative to the Corso, and may face a party wall.
    candidates=[i for i,p in enumerate(points) if i not in party and math.dist(p[:2],points[(i+1)%len(points)][:2])>195]
    originalfront=source.get_editor_property('front_edge_index')%len(points)
    def road_for_edge(i):
        mid=[(points[i][j]+points[(i+1)%len(points)][j])*.5 for j in range(3)]
        road=min(roads,key=lambda r:math.dist(vec(r.get_editor_property('spline').find_location_closest_to_world_location(unreal.Vector(*mid),unreal.SplineCoordinateSpace.WORLD))[:2],mid[:2]))
        distance=math.dist(vec(road.get_editor_property('spline').find_location_closest_to_world_location(unreal.Vector(*mid),unreal.SplineCoordinateSpace.WORLD))[:2],mid[:2])
        return distance,road
    frontedge=originalfront if originalfront in candidates else min(candidates,key=lambda i:road_for_edge(i)[0]) if candidates else originalfront
    a.set_editor_property('front_edge',frontedge)
    a.set_editor_property('party_wall_edges',party)
    a.set_editor_property('floor_height',2.7+(index%4)*.12)
    a.set_editor_property('decay',[.18,.48,.62,.42,.58,.83][index%6])
    a.set_editor_property('plaster_material',plasters[(index*5)%6]);a.set_editor_property('wood_material',woods[index%3])
    a.set_editor_property('balcony_density',.18 if family==EF.POPULAR else .42 if family==EF.PALAZZETTO else .3)
    a.set_editor_property('roof_rise',.55+.17*(index%4));a.set_editor_property('entrance_lift',.09+.045*(index%3))
    footprint=a.get_editor_property('footprint');footprint.clear_spline_points(False)
    for point in points:footprint.add_spline_point(unreal.Vector(point[0],point[1],location.z),unreal.SplineCoordinateSpace.WORLD,False)
    # World XY is unchanged. Z is recomputed by the generator; floor vertices stay horizontal.
    for i in range(len(points)):footprint.set_spline_point_type(i,unreal.SplinePointType.LINEAR,False)
    footprint.set_closed_loop(True,True)
    nearest=road_for_edge(frontedge)[1]
    a.set_editor_property('ground_actor',ground);a.set_editor_property('entrance_road',nearest)
    a.update_support();a.rebuild_house()
    error=a.get_editor_property('geometry_error')
    if error:report['errors'].append({'id':key,'error':error})
    assert all(math.dist(x[:2],y[:2])<.001 for x,y in zip(points,ring(a))),key
    source.set_actor_hidden_in_game(True);source.set_is_temporarily_hidden_in_editor(True);source.set_actor_enable_collision(False)
    for c in source.get_components_by_class(unreal.PrimitiveComponent):c.set_visibility(False);c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    source.set_folder_path('Mazzarino80/Campione_case_storiche/Perimetri_precedenti_nascosti')
    report['houses'].append({'id':key,'family':family.name,'seed':a.get_editor_property('seed'),'decay':a.get_editor_property('decay'),'road':nearest.get_actor_label(),'party_edges':list(a.get_editor_property('party_wall_edges')),'volumes':a.get_editor_property('generated_volumes'),'openings':a.get_editor_property('generated_openings'),'balconies':a.get_editor_property('generated_balconies'),'location':vec(a.get_actor_location())})
    unreal.log('HISTORIC_HOUSE '+json.dumps(report['houses'][-1]))
assert not report['errors'],report['errors']
report['landmarks_after']=[landmark(a) for a in actors if a.get_actor_label().startswith('M80_Recuperato_')]
assert report['landmarks_before']==report['landmarks_after']
assert levels.save_current_level()
(OUT/'generation.json').write_text(json.dumps(report,indent=2))
unreal.log('M80_HISTORIC_SAMPLE_SAVED 18 houses')
