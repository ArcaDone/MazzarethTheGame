"""Refresh two courtyard examples and report every failed constraint explicitly."""
import importlib
import json
import sys
import traceback
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
sys.path.insert(0,str(root/'Scripts'))
import mazzarino80_pcg_refresh_one as module
module=importlib.reload(module)
report={'map':'/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext',
        'completed':{},'errors':{}}
if not unreal.EditorLevelLibrary.load_level(report['map']):
    report['fatal']='Validation map not loaded'
else:
    for lot in ('1249069228','1249069205'):
        try:
            report['completed'][lot]=module.refresh(lot,save=False)
        except Exception:
            report['errors'][lot]=traceback.format_exc()
    report['saved']=bool(unreal.EditorLevelLibrary.save_current_level())
out=root/'Saved/Mazzarino80/PCG/architecture_pilot.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_ARCHITECTURE_PILOT '+str(out))
