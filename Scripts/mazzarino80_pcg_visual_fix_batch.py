"""Apply the visual corrections and rebuild the 18-house PCG sample in place."""
import importlib
import json
import sys
import traceback
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Scripts'))
OUT = ROOT / 'Saved/Mazzarino80/PCG/visual_fix_batch.json'
LEVEL = '/Game/Levels/Mazzarino80_CaseStoriche_Campione'


def write(report):
    OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')


report = {'level':LEVEL, 'completed':{}, 'errors':{}, 'saved':False}
write(report)
try:
    import mazzarino80_pcg_facade_macro_material as macro
    import mazzarino80_pcg_weathered_finish as weathered
    report['materials_updated'] = True
    write(report)
    if not unreal.EditorLevelLibrary.load_level(LEVEL):
        raise RuntimeError('Could not load the sample level')
    import mazzarino80_pcg_refresh_one as module
    module=importlib.reload(module)
    rows=json.loads((ROOT/'Research/Mazzarino80/PCG/Buildings_Test18.json').read_text(encoding='utf-8'))['buildings']
    for index,row in enumerate(rows):
        lot=row['building_id']
        try:
            result=module.refresh(lot,save=False)
            if not result['splines_preserved'] or not result['pcg_generated']:
                raise RuntimeError('Generation or spline preservation failed: '+str(result))
            report['completed'][lot]=result
        except Exception:
            report['errors'][lot]=traceback.format_exc()
        if index%3==2:
            report['saved']=bool(unreal.EditorLevelLibrary.save_current_level())
        write(report)
    report['saved']=bool(unreal.EditorLevelLibrary.save_current_level())
except Exception:
    report['fatal']=traceback.format_exc()
write(report)
unreal.log('M80_VISUAL_FIX_BATCH '+str(OUT))
