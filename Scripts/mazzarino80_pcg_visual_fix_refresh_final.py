"""Refresh all 18 PCG houses after the tapered damp/moss geometry change."""
import importlib
import json
import sys
import traceback
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
sys.path.insert(0,str(root/'Scripts'))
out=root/'Saved/Mazzarino80/PCG/visual_fix_refresh_final.json'
report={'completed':{},'errors':{},'saved':False}
def write():out.write_text(json.dumps(report,indent=2),encoding='utf-8')
write()
try:
    if not unreal.EditorLevelLibrary.load_level('/Game/Levels/Mazzarino80_CaseStoriche_Campione'):
        raise RuntimeError('Sample level unavailable')
    import mazzarino80_pcg_refresh_one as module
    module=importlib.reload(module)
    rows=json.loads((root/'Research/Mazzarino80/PCG/Buildings_Test18.json').read_text(encoding='utf-8'))['buildings']
    for index,row in enumerate(rows):
        lot=row['building_id']
        try:
            result=module.refresh(lot,save=False)
            if not result['splines_preserved'] or not result['pcg_generated']:
                raise RuntimeError('Invalid generation '+str(result))
            report['completed'][lot]=result
        except Exception:
            report['errors'][lot]=traceback.format_exc()
        if index%3==2:report['saved']=bool(unreal.EditorLevelLibrary.save_current_level())
        write()
    report['saved']=bool(unreal.EditorLevelLibrary.save_current_level())
except Exception:
    report['fatal']=traceback.format_exc()
write()
unreal.log('M80_VISUAL_FIX_REFRESH_FINAL '+str(out))
