"""Import the first exact roof slab for a visual and bounds check."""
import json
import traceback
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
lot='1249069247'
name='SM_PCG_Roof_'+lot
task=unreal.AssetImportTask()
task.filename=str(root/'Research/Mazzarino80/PCG/RoofMeshes_Source'/(name+'.obj'))
task.destination_path='/Game/Mazzarino80/PCG/Modules'
task.destination_name=name
task.automated=True
task.save=True
task.replace_existing=True
result={}
try:
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    result['imported']=[str(x) for x in task.imported_object_paths]
    mesh=unreal.load_asset(task.destination_path+'/'+name)
    result['asset']=str(mesh)
    if mesh:
        result['bounds']=str(mesh.get_bounds())
except Exception:
    result['error']=traceback.format_exc()
(root/'Saved/Mazzarino80/PCG/import_roof_test.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
