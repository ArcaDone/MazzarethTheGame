"""Temporary seed edit; run the companion restore script after verifying PCG instances."""
import importlib
import sys
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
sys.path.insert(0,str(root/'Scripts'))
import mazzarino80_pcg_refresh_one as module
module=importlib.reload(module)
catalog=unreal.load_asset('/Game/Mazzarino80/PCG/DA_Buildings_Test18')
record=next(d for d in catalog.get_editor_property('buildings')
            if d.get_editor_property('building_id')=='1249069275')
record.set_editor_property('variation_seed',1981)
print(module.refresh('1249069275',data_override=record,save=False))
