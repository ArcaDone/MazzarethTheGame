"""Persist Nanite usage for two materials used by the approved PCG modules."""
import json
from pathlib import Path
import unreal

paths=['/Game/Mazzarino80/Historic/Materials/M80_Terrazza_calce',
       '/Game/Mazzarino80/Historic/Materials/M80_Coppi_vecchi']
report={}
for path in paths:
    item={'exists':unreal.EditorAssetLibrary.does_asset_exist(path)}
    if item['exists']:
        material=unreal.load_asset(path)
        try:
            item['before']=material.get_editor_property('used_with_nanite')
            material.set_editor_property('used_with_nanite',True)
            item['after']=material.get_editor_property('used_with_nanite')
            item['saved']=unreal.EditorAssetLibrary.save_asset(path)
        except Exception as exc:
            item['error']=str(exc)
    report[path]=item
Path(unreal.Paths.project_dir(),'Saved/Mazzarino80/PCG/fix_nanite_materials.json').write_text(
    json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_FIX_NANITE '+str(report))
