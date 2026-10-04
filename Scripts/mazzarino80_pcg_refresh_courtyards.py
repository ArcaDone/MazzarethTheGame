"""Rebuild the two courtyard houses after resizing their masonry modules."""
import importlib
import json
import sys
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
sys.path.insert(0,str(root/'Scripts'))
import mazzarino80_pcg_refresh_one as refresh_module
refresh_module=importlib.reload(refresh_module)
report={}
for lot in ('1249069205','1249069228'):
    result=refresh_module.refresh(lot,save=False)
    assert result['splines_preserved'] and result['pcg_generated']
    report[lot]=result
report['saved']=bool(unreal.EditorLevelLibrary.save_current_level())
out=root/'Saved/Mazzarino80/PCG/refresh_courtyards.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_REFRESH_COURTYARDS '+str(out))
