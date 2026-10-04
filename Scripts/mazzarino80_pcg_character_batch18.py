"""Regenerate all 18 photo-informed houses in the isolated validation map."""
import importlib
import json
import sys
import traceback
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Scripts'))
OUT = ROOT / 'Saved/Mazzarino80/PCG/character_batch18.json'
LEVEL = '/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext'


def write(report):
    OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')


def main():
    rows = json.loads((ROOT/'Research/Mazzarino80/PCG/Buildings_Test18.json').read_text(encoding='utf-8'))['buildings']
    report = {'level':LEVEL, 'expected':len(rows), 'completed':{}, 'errors':{}, 'saved':False}
    write(report)
    try:
        if not unreal.EditorLevelLibrary.load_level(LEVEL):
            raise RuntimeError('Could not load the validation level')
        import mazzarino80_pcg_create_catalog_bp as catalog
        catalog = importlib.reload(catalog)
        catalog_result = json.loads((ROOT/'Saved/Mazzarino80/PCG/create_catalog_bp.json').read_text(encoding='utf-8'))
        if catalog_result.get('count') != 18 or catalog_result.get('errors') or catalog_result.get('fatal'):
            raise RuntimeError('Catalog creation failed: '+str(catalog_result))
        import mazzarino80_pcg_refresh_one as refresh_module
        refresh_module = importlib.reload(refresh_module)
        for index,row in enumerate(rows):
            lot = row['building_id']
            try:
                result = refresh_module.refresh(lot, save=False)
                if not result['splines_preserved'] or not result['pcg_generated']:
                    raise RuntimeError('Spline preservation or PCG generation failed: '+str(result))
                report['completed'][lot] = result
            except Exception:
                report['errors'][lot] = traceback.format_exc()
            if index%3 == 2:
                report['saved'] = bool(unreal.EditorLevelLibrary.save_current_level())
            write(report)
        report['saved'] = bool(unreal.EditorLevelLibrary.save_current_level())
    except Exception:
        report['fatal'] = traceback.format_exc()
    write(report)
    unreal.log('M80_CHARACTER_BATCH18 '+str(OUT))


main()
