import unreal,json
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
plan=json.loads((ROOT/'Research/Mazzarino80/casa_floresta_dependency_plan.json').read_text())
renames={p:'/Game/Mazzarino80/Library/Comune/'+p[6:] for p in plan['packages']+plan['known']}
for p in renames:assert unreal.load_asset(p),p
for old,new in sorted(renames.items(),key=lambda pair:pair[0].endswith('/CasaFloresta')):
    assert unreal.EditorAssetLibrary.rename_asset(old,new),old
assert unreal.EditorAssetLibrary.save_directory('/Game/Mazzarino80/Library/Comune',only_if_is_dirty=False,recursive=True)
(ROOT/'Research/Mazzarino80/casa_floresta_asset_renames.json').write_text(json.dumps(renames,indent=2))
unreal.log('M80_CASA_FLORESTA_READY '+str(len(renames)))
