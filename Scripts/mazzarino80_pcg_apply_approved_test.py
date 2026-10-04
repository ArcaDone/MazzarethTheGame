"""Replace one provisional PCG house with approved structure and original modules."""
import json
import importlib
import sys
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
sys.path.insert(0,str(root/'Scripts'))
import mazzarino80_pcg_create_data_assets as assets
assets=importlib.reload(assets)

lot='1249069275'
source=json.loads((root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))
house=source['houses'][lot]
catalog=json.loads((root/'Research/Mazzarino80/PCG/Buildings_Test18.json').read_text(encoding='utf-8'))
seed=next(b['variation_seed'] for b in catalog['buildings'] if b['building_id']==lot)
groups=house['stage_points']
for stage,points in groups.items():
    for n,point in enumerate(points):
        point['seed']=seed*100000+n
world=unreal.new_object(unreal.World,name='M80_PCG_ApprovedTestExportWorld')
result=assets.make_asset({'building_id':lot,'stage_points':groups},world)
actor=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
           if a.get_actor_label()=='BP_ProceduralBuilding_'+lot)
pcg=actor.get_component_by_class(unreal.PCGComponent)
pcg.cleanup(True)
pcg.set_editor_property('is_component_partitioned',False)
pcg.generate(True)
(root/'Saved/Mazzarino80/PCG/approved_test.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
