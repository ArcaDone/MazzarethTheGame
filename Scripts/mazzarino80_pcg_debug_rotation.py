import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
asset = unreal.load_asset('/Game/Mazzarino80/PCG/Buildings/PCGDA_Building_1249069247')
out = {}
out['component_cleanup_doc'] = unreal.PCGComponent.cleanup.__doc__
out['component_dirty_doc'] = unreal.PCGComponent.dirty_generated.__doc__
for label, rotation in {
    'keyword': unreal.Rotator(pitch=0, yaw=98.359, roll=0),
    'positional': unreal.Rotator(0, 98.359, 0),
}.items():
    out[label] = {'repr': str(rotation), 'quat': str(rotation.quaternion())}
for item in asset.get_editor_property('data').tagged_data:
    if 'Structure' in item.tags:
        point = item.data.get_points()[0]
        out['asset_structure'] = {'rotation': str(point.transform.rotation), 'transform': str(point.transform)}
        break
(root / 'Saved/Mazzarino80/PCG/debug_rotation.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
