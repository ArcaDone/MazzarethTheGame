"""Bring renamed dependencies across without overwriting existing library assets."""
import json,shutil
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
renames=json.loads((ROOT/'Research/Mazzarino80/casa_floresta_asset_renames.json').read_text())
count=0;reused=0
for old,new in renames.items():
    relative=new[6:]+'.uasset';src=ROOT/'Saved/M80CasaFlorestaResources/Content'/relative;target=ROOT/'Content'/relative
    assert src.exists(),src
    if target.exists():reused+=1;continue
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target);count+=1
print(json.dumps({'copied':count,'existing_reused':reused}))
