"""Record the current plaster parent for each of the 18 houses."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
rows = []
for entry in json.loads((root/'Saved/Mazzarino80/Historic/facade_finishes.json').read_text(encoding='utf-8')):
    material = unreal.load_asset(entry['material'])
    rows.append({'lot': entry['lot'], 'finish': entry['finish'],
                 'parent': material.parent.get_path_name() if material and material.parent else None})
(root/'Saved/Mazzarino80/PCG/facade_parents.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
