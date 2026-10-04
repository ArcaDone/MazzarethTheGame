"""Remove the remaining blue-grey cast from aged plaster instances."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
rows = json.loads((root/'Saved/Mazzarino80/PCG/facade_parents.json').read_text(encoding='utf-8'))
lib = unreal.MaterialEditingLibrary
palette = {1: (.76, .43, .17), 2: (.69, .40, .18), 4: (.78, .46, .18)}
updated = []
for row in rows:
    if row['finish'] != 'calce consumata':
        continue
    index = int(row['parent'].rsplit('_', 1)[-1])
    if index not in palette:
        continue
    lot = row['lot']
    material = unreal.load_asset('/Game/Mazzarino80/Historic/Materials/Case/MI_Calce_' + lot)
    if not material:
        raise RuntimeError('Missing house material ' + lot)
    variation = .94 + (int(lot[-2:]) % 8) * .018
    color = [round(v * variation, 4) for v in palette[index]]
    lib.set_material_instance_vector_parameter_value(material, 'Tinta', unreal.LinearColor(*color, 1))
    lib.set_material_instance_scalar_parameter_value(material, 'Contrasto_superficie', .25)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material):
        raise RuntimeError('Could not save house material ' + lot)
    updated.append({'lot': lot, 'index': index, 'tint': color})

out = root/'Saved/Mazzarino80/PCG/warm_facades.json'
out.write_text(json.dumps(updated, indent=2), encoding='utf-8')
unreal.log('M80_WARM_FACADES ' + str(out))
