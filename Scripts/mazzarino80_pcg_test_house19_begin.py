"""Place a temporary nineteenth record with approved modules outside the sample."""
import copy
import importlib
import json
import sys
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
sys.path.insert(0,str(root/'Scripts'))
import mazzarino80_pcg_create_data_assets as assets
assets=importlib.reload(assets)
lot='19_TEST'
source_lot='1249069275'
offset=unreal.Vector(12000,12000,0)
manifest=json.loads((root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))
groups=copy.deepcopy(manifest['houses'][source_lot]['stage_points'])
for stage,points in groups.items():
    for n,p in enumerate(points):
        p['location_cm'][0]+=offset.x
        p['location_cm'][1]+=offset.y
        p['seed']=1900100000+n
world=unreal.new_object(unreal.World,name='M80_PCG_House19World')
point_asset=assets.make_asset({'building_id':lot,'stage_points':groups},world)
master=unreal.load_asset('/Game/Mazzarino80/PCG/Graphs/PCG_Building_Master')
graph=unreal.load_asset('/Game/Mazzarino80/PCG/Buildings/PCG_Building_'+lot)
if not graph:
    graph=unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'PCG_Building_'+lot,'/Game/Mazzarino80/PCG/Buildings',unreal.PCGGraph,unreal.PCGGraphFactory())
if not list(graph.get_editor_property('nodes')):
    loader,settings=graph.add_node_of_type(unreal.PCGLoadDataAssetSettings)
    settings.asset=unreal.load_asset(point_asset['path'])
    node,subsettings=graph.add_node_of_type(unreal.PCGSubgraphSettings)
    subsettings.get_editor_property('subgraph_instance').set_editor_property('graph',master)
    graph.add_edge(loader,'Out',node,'In')
    graph.add_edge(node,'Out',graph.get_output_node(),'Out')
    unreal.EditorAssetLibrary.save_loaded_asset(graph)

catalog=unreal.load_asset('/Game/Mazzarino80/PCG/DA_Buildings_Test18')
source_data=next(d for d in catalog.get_editor_property('buildings')
                 if d.get_editor_property('building_id')==source_lot)
data=unreal.BuildingData()
for name in ('front_edge','party_wall_edges','family','primary_floors','floor_height_cm',
             'wall_thickness_cm','roof_type','roof_rise_cm','facade_type',
             'facade_material','roof_material','roof_mesh'):
    data.set_editor_property(name,source_data.get_editor_property(name))
data.set_editor_property('building_id',lot)
data.set_editor_property('footprint_world_cm',
    [unreal.Vector(p.x+offset.x,p.y+offset.y,p.z) for p in source_data.get_editor_property('footprint_world_cm')])
data.set_editor_property('ground_relationship','TemporaryValidationSite')
data.set_editor_property('variation_seed',19001)
data.set_editor_property('building_graph',graph)

subsystem=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=subsystem.get_all_level_actors()
source_actor=next(a for a in actors if a.get_actor_label()=='BP_ProceduralBuilding_'+source_lot)
name='BP_ProceduralBuilding_'+lot
if any(a.get_actor_label()==name for a in actors):
    raise RuntimeError('Temporary nineteenth actor already exists')
bp=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Mazzarino80/PCG/BP_ProceduralBuilding')
location=source_actor.get_actor_location()+offset
actor=subsystem.spawn_actor_from_class(bp,location)
actor.set_actor_label(name)
actor.set_actor_scale3d(source_actor.get_actor_scale3d())
actor.set_editor_property('building_data',data)
pcg=actor.get_component_by_class(unreal.PCGComponent)
pcg.set_editor_property('is_component_partitioned',False)
pcg.set_graph(graph)
pcg.generate(True)

report={'lot':lot,'source_lot':source_lot,'offset_cm':[offset.x,offset.y,offset.z],
        'record_id':data.get_editor_property('building_id'),'record_footprint_points':len(data.get_editor_property('footprint_world_cm')),
        'point_asset':point_asset,'graph':graph.get_path_name(),
        'expected_points':sum(len(points) for points in groups.values()),
        'actor':name,'catalog_still_18':len(catalog.get_editor_property('buildings'))==18}
(root/'Saved/Mazzarino80/PCG/house19_begin.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
