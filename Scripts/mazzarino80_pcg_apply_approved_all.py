"""Load the approved geometry and existing modules into all 18 staged PCG assets."""
import importlib
import json
import sys
import traceback
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
sys.path.insert(0,str(root/'Scripts'))
import mazzarino80_pcg_create_data_assets as assets
assets=importlib.reload(assets)
source=json.loads((root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))
catalog=json.loads((root/'Research/Mazzarino80/PCG/Buildings_Test18.json').read_text(encoding='utf-8'))
seeds={h['building_id']:h['variation_seed'] for h in catalog['buildings']}
world=unreal.new_object(unreal.World,name='M80_PCG_ApprovedExportWorld')
report={'assets':{},'errors':{}}
for lot,house in source['houses'].items():
    try:
        groups=house['stage_points']
        for stage,points in groups.items():
            for n,point in enumerate(points):
                point['seed']=seeds[lot]*100000+n
        report['assets'][lot]=assets.make_asset({'building_id':lot,'stage_points':groups},world)
    except Exception:
        report['errors'][lot]=traceback.format_exc()
(root/'Saved/Mazzarino80/PCG/apply_approved_all.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_PCG_APPROVED_ALL '+str(len(report['assets']))+' assets, '+str(len(report['errors']))+' errors')
