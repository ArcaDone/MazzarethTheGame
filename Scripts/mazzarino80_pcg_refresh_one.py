"""Rebuild one PCG house from its FBuildingData record, keeping other lots untouched.

Run from the Unreal Python console in a map containing the original source actor
and BP_ProceduralBuilding_<lot>. The original actor is a hidden geometry service:
its edited cable/downpipe splines remain in the contextual map.
"""
import importlib
import json
import math
import sys
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
SOURCE = ROOT / 'Research/Mazzarino80/PCG/BakedSource'
MANIFEST = SOURCE / 'approved_modules.json'
STAGES = ('Structure', 'Facades', 'Openings', 'Roofs', 'Details')
SECTION_STAGE = {0:'Structure',1:'Facades',2:'Roofs',3:'Roofs',4:'Details',5:'Details',
                 6:'Openings',7:'Facades',8:'Structure',9:'Details',10:'Facades',11:'Openings'}
MODULE_STAGE = {'Pietra_soglie_balconi':'Openings','Ferro_ringhiere':'Details',
                'Legno_portoni_persiane':'Openings','Vetri_incassati':'Openings',
                'Canalette_riparazioni':'Details','Vita_quotidiana':'Details',
                'Portoni_recuperati':'Openings','Vasi_recuperati':'Details',
                'Bucato_indumenti':'Details',
                'Coppi_tridimensionali':'Roofs','Balconi_completi':'Details'}


def vector(v):
    return [round(v.x, 6), round(v.y, 6), round(v.z, 6)]


def placement(role, stage, transform, mesh, material):
    q = transform.rotation
    return {'role':role, 'stage':stage, 'location_cm':vector(transform.translation),
            'rotation_quat':[round(q.x,8),round(q.y,8),round(q.z,8),round(q.w,8)],
            'scale':vector(transform.scale3d), 'mesh':mesh, 'material':material}


def asset_path(asset):
    return asset.get_path_name() if asset else ''


def spline_snapshot(actor):
    return {c.get_name():[vector(c.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD))
            for i in range(c.get_number_of_spline_points())]
            for c in actor.get_components_by_class(unreal.SplineComponent)
            if c.get_name() != 'Lotto_perimetro'}


def polygon_centroid(points):
    area2 = cx = cy = 0.0
    for a,b in zip(points, points[1:]+points[:1]):
        cross = a.x*b.y-b.x*a.y
        area2 += cross
        cx += (a.x+b.x)*cross
        cy += (a.y+b.y)*cross
    if abs(area2) < 1.0:
        raise RuntimeError('Degenerate house footprint')
    return cx/(3*area2), cy/(3*area2)


def add_character_details(groups, data, source, vertices):
    """Add authored, footprint-relative details without moving the edited service splines."""
    if not any(data.get_editor_property(name) for name in
               ('courtyard_gate','external_bathroom','facade_flue','cactus','ivy')):
        return
    front = data.get_editor_property('front_edge')
    a,b = vertices[front],vertices[(front+1)%len(vertices)]
    dx,dy=b.x-a.x,b.y-a.y
    length=math.hypot(dx,dy)
    if length < 100:
        raise RuntimeError('Street frontage too short for contextual details')
    along=(dx/length,dy/length)
    signed=sum(v.x*vertices[(i+1)%len(vertices)].y-vertices[(i+1)%len(vertices)].x*v.y
               for i,v in enumerate(vertices))
    outward=(dy/length,-dx/length) if signed>0 else (-dy/length,dx/length)
    inward=(-outward[0],-outward[1])
    project=lambda p,axis:p.x*axis[0]+p.y*axis[1]
    s_values=[project(v,along) for v in vertices]
    t_values=[project(v,inward) for v in vertices]
    s0,s1=min(s_values),max(s_values)
    t0,t1=min(t_values),max(t_values)
    width,depth=s1-s0,t1-t0
    smid=(s0+s1)*.5
    road=source.get_editor_property('entrance_road')
    road_spline=road.get_editor_property('spline') if road else None

    def xy(s,t):
        return s*along[0]+t*inward[0],s*along[1]+t*inward[1]

    def road_z(x,y):
        if not road_spline:
            return a.z
        return road_spline.find_location_closest_to_world_location(
            unreal.Vector(x,y,a.z),unreal.SplineCoordinateSpace.WORLD).z

    def mesh(path):
        asset=unreal.load_asset(path)
        if not asset:
            raise RuntimeError('Missing character detail mesh '+path)
        return asset

    def append(role, stage, asset, xyz, yaw=0, scale=(1,1,1), material=None):
        transform=unreal.Transform(location=unreal.Vector(*xyz),
            rotation=unreal.Rotator(pitch=0,yaw=yaw,roll=0),scale=unreal.Vector(*scale))
        mat=material or asset.get_material(0)
        groups[stage].append(placement(role,stage,transform,asset_path(asset),asset_path(mat)))

    if data.get_editor_property('courtyard_gate'):
        gap=width*source.get_editor_property('courtyard_width')
        if gap < 500 or depth < 650 or str(data.get_editor_property('family')).upper() != 'COURTYARD':
            raise RuntimeError('Courtyard gate requested on an incompatible lot')
        cube=mesh('/Engine/BasicShapes/Cube')
        gate_width=280.0
        half_wall=(gap-gate_width)*.5
        if half_wall < 50:
            raise RuntimeError('Insufficient courtyard wall beside gate')
        x,y=xy(smid,t0+22)
        z=road_z(x,y)-25
        # An open iron grille keeps the yard legible from the street. A solid
        # roller shutter visually reads as a garage, so use simple iron bars.
        iron=mesh('/Game/Mazzarino80/Historic/Materials/M80_Ferro_ossidato')
        gate_yaw=math.degrees(math.atan2(along[1],along[0]))
        for index in range(15):
            bx,by=xy(smid-gate_width*.5+index*gate_width/14,t0+22)
            append('courtyard_gate_bar_%02d'%index,'Openings',cube,
                   (bx,by,z+122),gate_yaw,(.045,.045,2.44),iron)
        for height in (18,118,230):
            append('courtyard_gate_rail_%03d'%height,'Openings',cube,
                   (x,y,z+height),gate_yaw,(gate_width/100,.065,.055),iron)
        stone=unreal.load_asset('/Game/Mazzarino80/Historic/Materials/M80_Muratura_locale_0')
        if not stone:
            raise RuntimeError('Missing courtyard masonry material')
        wall_yaw=math.degrees(math.atan2(along[1],along[0]))
        # All sections share a level top and extend below the lowest support.
        # This avoids the stair-step silhouette and gaps on a sloping street.
        columns=max(1,math.ceil(half_wall/100))
        block_width=half_wall/columns
        for side in (-1,1):
            start=smid+side*gate_width*.5
            end=start+side*half_wall
            end_x,end_y=xy(end,t0+22)
            top=max(road_z(x,y),road_z(end_x,end_y))+245
            for column in range(columns):
                wall_s=start+side*(column+.5)*block_width
                wx,wy=xy(wall_s,t0+22)
                ground=min(road_z(wx,wy),road_z(end_x,end_y),road_z(x,y))-60
                append('courtyard_wall_%+d_%02d'%(side,column),
                       'Structure',cube,(wx,wy,(ground+top)*.5),wall_yaw,
                       (block_width/100,.44,(top-ground)/100),stone)

    if data.get_editor_property('external_bathroom'):
        if not data.get_editor_property('courtyard_gate'):
            raise RuntimeError('Exterior bathroom requires an enclosed courtyard')
        bath=mesh('/Game/City_of_Brass_Enviroment/Meshes/Corridor_A/Corridor_A_Box02_Ex')
        scale=.36
        gap=width*source.get_editor_property('courtyard_width')
        bath_width=bath.get_bounds().box_extent.x*2*scale
        bath_depth=bath.get_bounds().box_extent.y*2*scale
        yard_depth=depth*source.get_editor_property('courtyard_depth')
        if bath_width+80>=gap or bath_depth+120>=yard_depth:
            raise RuntimeError('Exterior bathroom does not fit the courtyard')
        center_s=smid+gap*.5-bath_width*.5-35
        # Rear masonry is the support: keep the small timber privy against it.
        center_t=t0+yard_depth-bath_depth*.5-12
        cx,cy=xy(center_s,center_t)
        bath_yaw=math.degrees(math.atan2(along[1],along[0]))+(0 if signed>0 else 180)
        rad=math.radians(bath_yaw)
        origin=bath.get_bounds().origin
        ox=origin.x*math.cos(rad)-origin.y*math.sin(rad)
        oy=origin.x*math.sin(rad)+origin.y*math.cos(rad)
        bottom=origin.z-bath.get_bounds().box_extent.z
        append('external_bathroom','Details',bath,
               (cx-ox*scale,cy-oy*scale,a.z+data.get_editor_property('floor_height_cm')+15-bottom*scale),bath_yaw,
               (scale,scale,scale))
        support=mesh('/Engine/BasicShapes/Cube')
        stone=unreal.load_asset('/Game/Mazzarino80/Historic/Materials/M80_Pietra_modesta')
        for side in (-1,1):
            bx,by=xy(center_s+side*bath_width*.35,center_t+10)
            append('external_bathroom_corbel_%+d'%side,'Details',support,
                   (bx,by,a.z+data.get_editor_property('floor_height_cm')+8),
                   math.degrees(math.atan2(along[1],along[0])),
                   (.14,(bath_depth+35)/100,.16),stone)

    if data.get_editor_property('facade_flue'):
        pipe=mesh('/Engine/BasicShapes/Cylinder')
        x,y=xy(project(a,along)+length*.84,project(a,inward)-14)
        base=a.z+data.get_editor_property('floor_height_cm')*.55
        top=a.z+data.get_editor_property('primary_floors')*data.get_editor_property('floor_height_cm')+35
        height=top-base
        append('facade_flue','Details',pipe,(x,y,(base+top)*.5),0,
               (.12,.12,height/100),
               unreal.load_asset('/Game/Mazzarino80/Historic/Materials/M80_Canaletta_pietra_opaca'))

    if data.get_editor_property('cactus'):
        cactus=mesh('/Game/Megascans/3D_Assets/Cactus_udugdfvfa/S_Cactus_udugdfvfa_lod3_Var1')
        x,y=xy(project(a,along)+length*.91,project(a,inward)-72)
        bounds=cactus.get_bounds()
        append('street_cactus','Details',cactus,(x,y,road_z(x,y)-(bounds.origin.z-bounds.box_extent.z)))

    if data.get_editor_property('ivy'):
        ivy=mesh('/Game/Mazzarino80/Library/Comune/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var3_lod1')
        x,y=xy(project(a,along)+length*.08,project(a,inward)-8)
        yaw=math.degrees(math.atan2(outward[1],outward[0]))-90
        scale=3.4
        bounds=ivy.get_bounds()
        bottom=bounds.origin.z-bounds.box_extent.z
        append('facade_ivy','Details',ivy,(x,y,road_z(x,y)-bottom*scale),yaw,(scale,scale,scale))


def refresh(lot, data_override=None, save=False):
    catalog = unreal.load_asset('/Game/Mazzarino80/PCG/DA_Buildings_Test18')
    records = {d.get_editor_property('building_id'):d for d in catalog.get_editor_property('buildings')}
    data = data_override or records[lot]
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = subsystem.get_all_level_actors()
    source = next(a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)
                  and a.get_editor_property('lot_id') == lot)
    target = next(a for a in actors if a.get_actor_label() == 'BP_ProceduralBuilding_'+lot)
    before_splines = spline_snapshot(source)
    before_points = sum(c.get_instance_count() for c in target.get_components_by_class(unreal.InstancedStaticMeshComponent))

    source.modify()
    source.set_editor_property('seed', data.get_editor_property('variation_seed'))
    source.set_editor_property('floors_override', data.get_editor_property('primary_floors'))
    source.set_editor_property('floor_height', data.get_editor_property('floor_height_cm') / 100.0)
    source.set_editor_property('wall_thickness', data.get_editor_property('wall_thickness_cm') / 100.0)
    source.set_editor_property('upper_brick_floor', data.get_editor_property('upper_brick_floor'))
    source.set_editor_property('masonry_loss', data.get_editor_property('masonry_loss'))
    upper_brick_material = data.get_editor_property('upper_brick_material')
    if upper_brick_material:
        source.set_editor_property('upper_brick_material',upper_brick_material)
    source.set_editor_property('roof_rise', data.get_editor_property('roof_rise_cm') / 100.0)
    source.set_editor_property('front_edge', data.get_editor_property('front_edge'))
    source.set_editor_property('party_wall_edges', data.get_editor_property('party_wall_edges'))
    facade_material = data.get_editor_property('facade_material')
    roof_material = data.get_editor_property('roof_material')
    if facade_material:
        source.set_editor_property('plaster_material', facade_material)
    if roof_material:
        source.set_editor_property('roof_material', roof_material)
    stone_trim=unreal.load_asset('/Game/Mazzarino80/Historic/Materials/M80_Pietra_modesta')
    if stone_trim:
        source.set_editor_property('stone_material',stone_trim)
    if lot in ('1249069205','1249069228','1249069246','1249069271'):
        moss=unreal.load_asset('/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Mossy_Rock_wgnwbcd/MI_Mossy_Rock_wgnwbcd_2K')
        if moss:
            source.set_editor_property('damp_material',moss)
    family = str(data.get_editor_property('family')).upper()
    source.set_editor_property('family', getattr(unreal.M80HouseFamily, family))
    footprint = source.get_editor_property('footprint')
    wanted = data.get_editor_property('footprint_world_cm')
    current = [footprint.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD)
               for i in range(footprint.get_number_of_spline_points())]
    changed = len(wanted) != len(current) or any((a-b).length() > .1 for a,b in zip(wanted,current))
    if changed:
        footprint.modify()
        footprint.clear_spline_points(False)
        for point in wanted:
            footprint.add_spline_point(point, unreal.SplineCoordinateSpace.WORLD, False)
        footprint.set_closed_loop(True, True)
    source.rebuild_house()
    after_splines = spline_snapshot(source)
    if before_splines != after_splines:
        raise RuntimeError('Service splines changed during isolated rebuild of '+lot)

    exported = [str(p) for p in source.export_pcg_surface_sections(str(SOURCE))]
    section_files = {int(Path(p).stem.split('_S')[-1]):Path(p) for p in exported}
    groups = {stage:[] for stage in STAGES}
    surface = source.get_editor_property('surface')
    for section, file in section_files.items():
        stage = SECTION_STAGE[section]
        mesh = f'/Game/Mazzarino80/PCG/ApprovedModules/SM_PCG_Source_{lot}_S{section}'
        groups[stage].append(placement(f'surface_section_{section}', stage, surface.get_world_transform(),
                                       mesh+'.'+mesh.rsplit('/',1)[-1], asset_path(surface.get_material(section))))
    component_counts = {}
    for component in source.get_components_by_class(unreal.InstancedStaticMeshComponent):
        count = component.get_instance_count()
        if not count:
            continue
        name = component.get_name()
        stage = MODULE_STAGE.get(name,'Details')
        mesh = asset_path(component.get_editor_property('static_mesh'))
        material = asset_path(component.get_material(0))
        for i in range(count):
            groups[stage].append(placement(name,stage,component.get_instance_transform(i,world_space=True),mesh,material))
        component_counts[name] = count
    if data.get_editor_property('rooftop_tank'):
        mesh = data.get_editor_property('rooftop_tank_mesh')
        if not mesh:
            raise RuntimeError('Rooftop tank enabled without a mesh for '+lot)
        vertices = list(data.get_editor_property('footprint_world_cm'))
        x,y = polygon_centroid(vertices)
        z = sum(v.z for v in vertices)/len(vertices) + data.get_editor_property('primary_floors')*data.get_editor_property('floor_height_cm') + 8
        a,b = vertices[data.get_editor_property('front_edge')],vertices[(data.get_editor_property('front_edge')+1)%len(vertices)]
        dx,dy=b.x-a.x,b.y-a.y
        front_length=math.hypot(dx,dy)
        signed=sum(v.x*vertices[(i+1)%len(vertices)].y-vertices[(i+1)%len(vertices)].x*v.y for i,v in enumerate(vertices))
        outward=(dy/front_length,-dx/front_length) if signed>0 else (-dy/front_length,dx/front_length)
        # Shift the silhouette toward the street while retaining a roof margin.
        shift=105 if int(lot)%2 else 145
        x+=outward[0]*shift
        y+=outward[1]*shift
        yaw = math.degrees(math.atan2(b.y-a.y,b.x-a.x))
        transform = unreal.Transform(location=unreal.Vector(x,y,z),rotation=unreal.Rotator(pitch=0,yaw=yaw,roll=0),scale=unreal.Vector(1,1,1))
        groups['Details'].append(placement('rooftop_water_tank','Details',transform,asset_path(mesh),asset_path(mesh.get_material(0))))
        vessel = data.get_editor_property('tank_vessel_mesh')
        vessel_material = data.get_editor_property('tank_vessel_material')
        if not vessel or not vessel_material:
            raise RuntimeError('Rooftop tank vessel or material missing for '+lot)
        support_height = mesh.get_bounds().box_extent.z*2
        if lot == '1249069271':
            # A recovered wooden water butt breaks the repeated cylinder silhouette.
            vessel = unreal.load_asset('/Game/Mazzarino80/Library/Comune/OldWestAssets/OldWestVol5/VOL5/Meshes/SM_Barrels_NN_01a')
            if not vessel:
                raise RuntimeError('Alternate water butt missing')
            vessel_material = vessel.get_material(0)
            bounds=vessel.get_bounds()
            scale=min(125/max(1,bounds.box_extent.x*2,bounds.box_extent.y*2),
                      150/max(1,bounds.box_extent.z*2))
            vessel_scale=(scale,scale,scale)
        else:
            vessel_scale=(1.15,1.15,1.2)
        vessel_bottom = (vessel.get_bounds().origin.z-vessel.get_bounds().box_extent.z)*vessel_scale[2]
        vessel_transform = unreal.Transform(
            location=unreal.Vector(x,y,z+support_height-vessel_bottom),
            rotation=unreal.Rotator(pitch=0,yaw=yaw,roll=0),scale=unreal.Vector(*vessel_scale))
        groups['Details'].append(placement('rooftop_water_vessel','Details',vessel_transform,
                                            asset_path(vessel),asset_path(vessel_material)))
        component_counts['rooftop_water_tank'] = 2
    add_character_details(groups,data,source,list(data.get_editor_property('footprint_world_cm')))
    total = 0
    seed = data.get_editor_property('variation_seed')
    for points in groups.values():
        for i,p in enumerate(points):
            p['seed'] = seed*100000+i
        total += len(points)

    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    manifest['houses'][lot] = {'label':source.get_actor_label(),'surface_exports':exported,
                                'component_counts':component_counts,'stage_points':groups}
    MANIFEST.write_text(json.dumps(manifest,indent=2),encoding='utf-8')

    tasks = []
    for section,file in section_files.items():
        task=unreal.AssetImportTask()
        task.filename=str(file)
        task.destination_path='/Game/Mazzarino80/PCG/ApprovedModules'
        task.destination_name=f'SM_PCG_Source_{lot}_S{section}'
        task.automated=True
        task.save=True
        task.replace_existing=True
        tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

    sys.path.insert(0,str(ROOT/'Scripts'))
    import mazzarino80_pcg_create_data_assets as assets
    assets = importlib.reload(assets)
    world = unreal.new_object(unreal.World,name='M80_PCG_RefreshWorld')
    asset_result = assets.make_asset({'building_id':lot,'stage_points':groups},world)
    target.modify()
    target.set_actor_hidden_in_game(False)
    target.set_editor_property('building_data',data)
    pcg = target.get_component_by_class(unreal.PCGComponent)
    pcg.modify()
    pcg.set_editor_property('is_component_partitioned',False)
    unreal.PCGBlueprintHelpers.flush_pcg_cache()
    pcg.generate(True)
    if save:
        unreal.EditorLevelLibrary.save_current_level()
    report={'lot':lot,'footprint_changed':changed,'old_points':before_points,
            'new_points':total,'section_count':len(section_files),'asset':asset_result,
            'splines_preserved':before_splines == after_splines,
            'pcg_generated':pcg.generated,'partitioned':pcg.is_component_partitioned}
    (ROOT/'Saved/Mazzarino80/PCG/refresh_one.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    # Edit this ID to rebuild another catalog entry from the Unreal Python console.
    print(refresh('1249069275',save=True))
