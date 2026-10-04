"""Duplicate the original sample into a safe, fully contextual PCG staging map."""
import json
from pathlib import Path
import unreal

source='/Game/Levels/Mazzarino80_CaseStoriche_Campione'
target='/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext'
report={'source':source,'target':target,'exists_before':unreal.EditorAssetLibrary.does_asset_exist(target)}
if not report['exists_before']:
    report['duplicated']=str(unreal.EditorAssetLibrary.duplicate_asset(source,target))
report['exists_after']=unreal.EditorAssetLibrary.does_asset_exist(target)
report['saved']=unreal.EditorAssetLibrary.save_asset(target)
Path(unreal.Paths.project_dir(),'Saved/Mazzarino80/PCG/create_context_map.json').write_text(
    json.dumps(report,indent=2),encoding='utf-8')
