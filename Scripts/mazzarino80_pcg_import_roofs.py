"""Import the exact footprint roof slabs used by the PCG roof stage."""
import json
import traceback
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
manifest=json.loads((root/'Research/Mazzarino80/PCG/RoofMeshes_Source/manifest.json').read_text(encoding='utf-8'))
dest='/Game/Mazzarino80/PCG/Modules'
tasks=[]
for lot,info in manifest.items():
    name='SM_PCG_Roof_'+lot
    if unreal.load_asset(dest+'/'+name):
        continue
    task=unreal.AssetImportTask()
    task.filename=info['path']
    task.destination_path=dest
    task.destination_name=name
    task.automated=True
    task.save=True
    task.replace_existing=False
    tasks.append(task)
result={'requested':len(tasks),'meshes':{},'errors':{}}
try:
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
except Exception:
    result['import_error']=traceback.format_exc()
for lot in manifest:
    try:
        mesh=unreal.load_asset(dest+'/SM_PCG_Roof_'+lot)
        if not mesh:
            raise RuntimeError('StaticMesh missing')
        result['meshes'][lot]={'path':mesh.get_path_name(),'bounds':str(mesh.get_bounds())}
    except Exception:
        result['errors'][lot]=traceback.format_exc()
(root/'Saved/Mazzarino80/PCG/import_roofs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
