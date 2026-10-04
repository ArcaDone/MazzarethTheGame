"""Import exported surface sections as stage-specific PCG Static Mesh modules."""
import json
import traceback
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
source=root/'Research/Mazzarino80/PCG/BakedSource'
manifest=json.loads((source/'approved_modules.json').read_text(encoding='utf-8'))
destination='/Game/Mazzarino80/PCG/ApprovedModules'
REIMPORT=True
tasks=[]
for lot,house in manifest['houses'].items():
    for path in house['surface_exports']:
        file=Path(path)
        if not file.is_absolute():
            file=Path(unreal.Paths.convert_relative_path_to_full(str(file)))
        section=file.stem.split('_S')[-1]
        name=f'SM_PCG_Source_{lot}_S{section}'
        if unreal.load_asset(destination+'/'+name) and not REIMPORT:
            continue
        task=unreal.AssetImportTask()
        task.filename=str(file)
        task.destination_path=destination
        task.destination_name=name
        task.automated=True
        task.save=True
        task.replace_existing=REIMPORT
        tasks.append(task)
result={'requested':len(tasks),'imported':[],'errors':{}}
try:
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
except Exception:
    result['errors']['batch']=traceback.format_exc()
for lot,house in manifest['houses'].items():
    for path in house['surface_exports']:
        section=Path(path).stem.split('_S')[-1]
        name=f'SM_PCG_Source_{lot}_S{section}'
        asset=unreal.load_asset(destination+'/'+name)
        if asset:
            result['imported'].append(asset.get_path_name())
        else:
            result['errors'][name]='missing after import'
(root/'Saved/Mazzarino80/PCG/import_approved_modules.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
