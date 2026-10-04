import unreal,json
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
manifest=json.loads((ROOT/'Research/Mazzarino80/comune_building_resources_manifest.json').read_text())
renames={p:'/Game/Mazzarino80/Library/Comune/'+p[6:] for p in manifest['packages']}
for p in renames: assert unreal.load_asset(p),p
for old,new in sorted(renames.items()):
    assert unreal.EditorAssetLibrary.rename_asset(old,new),old
assert unreal.EditorAssetLibrary.save_directory('/Game/Mazzarino80/Library/Comune',only_if_is_dirty=False,recursive=True)
bounds={}
for old in manifest['selected']:
    a=unreal.load_asset(renames[old])
    row={'path':renames[old],'class':a.get_class().get_name()}
    if isinstance(a,unreal.StaticMesh):
        b=a.get_bounds()
        row.update(origin=list(b.origin.to_tuple()),extent=list(b.box_extent.to_tuple()))
    bounds[old]=row
(ROOT/'Research/Mazzarino80/comune_building_asset_renames.json').write_text(json.dumps(renames,indent=2))
(ROOT/'Research/Mazzarino80/comune_building_asset_info.json').write_text(json.dumps(bounds,indent=2))
unreal.log('M80_BUILDING_LIBRARY_READY '+str(len(renames)))
