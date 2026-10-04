"""Duplicate the persisted PCG stage map and explicitly save the new package."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
stage = '/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext'
target = '/Game/Levels/Mazzarino80_CaseStoriche_Campione'
disk = root/'Content/Levels/Mazzarino80_CaseStoriche_Campione.umap'
if not unreal.EditorAssetLibrary.does_asset_exist(stage):
    raise RuntimeError('Staged PCG map missing')
if disk.exists():
    raise RuntimeError('Target disk package already exists; refusing to overwrite')
created = bool(unreal.EditorAssetLibrary.duplicate_asset(stage,target))
saved = unreal.EditorAssetLibrary.save_asset(target) if created else False
report = {'stage':stage,'target':target,'created':created,'saved':saved,
          'disk_exists':disk.exists(),'disk_bytes':disk.stat().st_size if disk.exists() else 0}
(root/'Saved/Mazzarino80/PCG/persist_sample.json').write_text(
    json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_PERSIST_SAMPLE '+str(report))
if not saved or not disk.exists():
    raise RuntimeError('Target sample was not saved to disk')
