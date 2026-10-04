"""Enable imported brick materials for instanced PCG geometry."""
import json
import traceback
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir())
OUT=ROOT/'Saved/Mazzarino80/PCG/fix_brick_materials.json'
paths=('/Game/Megapack/Material/Favela/M_Bricks_01',
       '/Game/Megapack/Material/Favela/M_Bricks_Bland_01')
report={'materials':{},'errors':{}}
for path in paths:
    try:
        material=unreal.load_asset(path)
        if not isinstance(material,unreal.Material):
            raise RuntimeError('Expected Material: '+path)
        before=bool(material.get_editor_property('used_with_instanced_static_meshes'))
        material.modify()
        material.set_editor_property('used_with_instanced_static_meshes',True)
        saved=bool(unreal.EditorAssetLibrary.save_loaded_asset(material))
        report['materials'][path]={'before':before,
                                   'after':bool(material.get_editor_property('used_with_instanced_static_meshes')),
                                   'saved':saved}
    except Exception:
        report['errors'][path]=traceback.format_exc()
OUT.write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_BRICK_MATERIALS '+str(OUT))
