"""Populate the native FBuildingData catalog and create BP_ProceduralBuilding."""
import json
import traceback
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
records = json.loads((root/'Research/Mazzarino80/PCG/Buildings_Test18.json').read_text(encoding='utf-8'))['buildings']
dest='/Game/Mazzarino80/PCG'
report={'count':0,'errors':{},'classes':{}}


def building_data(record):
    lot=record['building_id']
    data=unreal.BuildingData()
    properties={
        'building_id':lot,
        'footprint_world_cm':[unreal.Vector(*p) for p in record['footprint_world_cm']],
        'front_edge':int(record['front_edge']),
        'party_wall_edges':json.loads(record['party_wall_edges']),
        'entrance_road':unreal.SoftObjectPath(record['entrance_road_path']),
        'ground_actor':unreal.SoftObjectPath(record['ground_actor_path']),
        'family':record['family'],
        'primary_floors':int(record['primary_floors']),
        'floor_height_cm':float(record['floor_height_cm']),
        'wall_thickness_cm':float(record['wall_thickness_cm']),
        'roof_type':record['roof_type'],
        'roof_rise_cm':float(record['roof_rise_cm']),
        'facade_type':record['facade_type'],
        'character_profile':record.get('character_profile',''),
        'upper_brick_floor':bool(record.get('upper_brick_floor',False)),
        'masonry_loss':float(record.get('masonry_loss',0.0)),
        'rooftop_tank':bool(record.get('rooftop_tank',False)),
        'courtyard_gate':bool(record.get('courtyard_gate',False)),
        'external_bathroom':bool(record.get('external_bathroom',False)),
        'facade_flue':bool(record.get('facade_flue',False)),
        'cactus':bool(record.get('cactus',False)),
        'ivy':bool(record.get('ivy',False)),
        'ground_relationship':record['ground_relationship'],
        'variation_seed':int(record['variation_seed']),
        'facade_material':unreal.load_asset(record['materials']['plaster_material']),
        'roof_material':unreal.load_asset(record['materials']['terrace_material'] if record['roof_type']=='Terrace' else record['materials']['roof_material']),
        'upper_brick_material':unreal.load_asset(record.get('upper_brick_material','')),
        'roof_mesh':unreal.load_asset('/Game/Mazzarino80/PCG/Modules/SM_PCG_Roof_'+lot),
        'rooftop_tank_mesh':unreal.load_asset(record.get('rooftop_tank_mesh','')),
        'tank_vessel_mesh':unreal.load_asset(record.get('tank_vessel_mesh','')),
        'tank_vessel_material':unreal.load_asset(record.get('tank_vessel_material','')),
        'building_graph':unreal.load_asset('/Game/Mazzarino80/PCG/Buildings/PCG_Building_'+lot),
    }
    for key,value in properties.items():
        data.set_editor_property(key,value)
    return data


try:
    report['classes']={'data':str(unreal.BuildingData),'catalog':str(unreal.MazzarinoPCGBuildingCatalog),
                       'actor':str(unreal.MazzarinoProceduralBuilding)}
    catalog=unreal.load_asset(dest+'/DA_Buildings_Test18')
    if not catalog:
        factory=unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class',unreal.MazzarinoPCGBuildingCatalog)
        catalog=unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_Buildings_Test18',dest,
                   unreal.MazzarinoPCGBuildingCatalog,factory)
    entries=[]
    for record in records:
        try:
            entries.append(building_data(record))
        except Exception:
            report['errors'][record['building_id']]=traceback.format_exc()
    catalog.set_editor_property('buildings',entries)
    report['count']=len(entries)
    report['catalog_saved']=unreal.EditorAssetLibrary.save_loaded_asset(catalog)
    bp=unreal.load_asset(dest+'/BP_ProceduralBuilding')
    if not bp:
        factory=unreal.BlueprintFactory()
        factory.set_editor_property('parent_class',unreal.MazzarinoProceduralBuilding)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_ProceduralBuilding',dest,unreal.Blueprint,factory)
    report['blueprint']=str(bp)
    report['blueprint_saved']=bool(bp and unreal.EditorAssetLibrary.save_loaded_asset(bp))
except Exception:
    report['fatal']=traceback.format_exc()
(root/'Saved/Mazzarino80/PCG/create_catalog_bp.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
