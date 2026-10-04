"""Finish the rooftop cistern on its two validation houses."""
import importlib
import json
import sys
import traceback
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir())
sys.path.insert(0,str(ROOT/'Scripts'))
OUT=ROOT/'Saved/Mazzarino80/PCG/tank_update.json'
report={'lots':{},'saved':False}
try:
    if not unreal.EditorLevelLibrary.load_level('/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext'):
        raise RuntimeError('Validation map unavailable')
    import mazzarino80_pcg_create_catalog_bp as catalog
    importlib.reload(catalog)
    import mazzarino80_pcg_refresh_one as refresh_module
    refresh_module=importlib.reload(refresh_module)
    for lot in ('1249069213','1249069271'):
        report['lots'][lot]=refresh_module.refresh(lot,save=False)
        OUT.write_text(json.dumps(report,indent=2),encoding='utf-8')
    report['saved']=bool(unreal.EditorLevelLibrary.save_current_level())
except Exception:
    report['error']=traceback.format_exc()
OUT.write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_TANK_UPDATE '+str(OUT))
