"""Prove an edited seed changes only one house, then restore the approved state."""
import hashlib
import importlib
import json
import sys
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
sys.path.insert(0,str(root/'Scripts'))
import mazzarino80_pcg_refresh_one as module
module = importlib.reload(module)
lot = '1249069275'
manifest = root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json'
before = json.loads(manifest.read_text(encoding='utf-8'))['houses']
catalog = unreal.load_asset('/Game/Mazzarino80/PCG/DA_Buildings_Test18')
record = next(d for d in catalog.get_editor_property('buildings')
              if d.get_editor_property('building_id') == lot)
original_seed = record.get_editor_property('variation_seed')

def digest(house):
    payload = json.dumps(house['stage_points'],sort_keys=True).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

report = {'lot':lot,'original_seed':original_seed}
try:
    record.set_editor_property('variation_seed',original_seed+1)
    report['edited_refresh'] = module.refresh(lot, data_override=record, save=False)
    edited = json.loads(manifest.read_text(encoding='utf-8'))['houses']
    report['target_changed'] = digest(before[lot]) != digest(edited[lot])
    report['other_lots_unchanged'] = all(digest(before[k]) == digest(edited[k]) for k in before if k != lot)
finally:
    record.set_editor_property('variation_seed',original_seed)
    report['restored_refresh'] = module.refresh(lot, data_override=record, save=True)
    restored = json.loads(manifest.read_text(encoding='utf-8'))['houses']
    report['target_restored'] = digest(before[lot]) == digest(restored[lot])
    report['all_other_lots_still_unchanged'] = all(digest(before[k]) == digest(restored[k]) for k in before if k != lot)

(root/'Saved/Mazzarino80/PCG/test_isolated_edit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
