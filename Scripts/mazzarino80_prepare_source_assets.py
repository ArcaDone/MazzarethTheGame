"""Rename assets in the isolated source copy before bringing them into the game."""
import json
from pathlib import Path
import unreal
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
dependency=json.loads((ROOT/'Research/Mazzarino80/comune_road_dependencies.json').read_text())
packages=set(p for d in dependency.values() for p,v in d.items() if not v.get('missing'))
renames={p:'/Game/Mazzarino80/RoadSource/'+p[6:] for p in packages}
for p in packages: assert unreal.load_asset(p), p
for old,new in sorted(renames.items(),key=lambda x:('Spline_' in x[0],x[0])):
    assert unreal.EditorAssetLibrary.rename_asset(old,new),old
unreal.EditorAssetLibrary.save_directory('/Game/Mazzarino80/RoadSource',only_if_is_dirty=False,recursive=True)
(ROOT/'Research/Mazzarino80/comune_asset_renames.json').write_text(json.dumps(renames,indent=2),encoding='utf-8')
unreal.log('M80_SOURCE_RENAME_DONE '+str(len(renames)))
