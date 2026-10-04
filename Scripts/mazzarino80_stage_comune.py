import json, shutil, re
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
SRC=Path(r'D:\UE5Projects\Comune\Content')
STAGE=ROOT/'Saved/M80ComuneInspection'
dependencies=json.loads((ROOT/'Research/Mazzarino80/comune_road_dependencies.json').read_text())
packages=set(p for d in dependencies.values() for p,v in d.items() if not v.get('missing'))
for package in packages:
    relative=package[6:]+'.uasset'
    target=STAGE/'Content'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SRC/relative,target)
shutil.copy2(SRC/'Comune.umap',STAGE/'Content/Comune.umap')
actor_count=0
for path in (SRC/'__ExternalActors__/Comune').rglob('*.uasset'):
    data=path.read_bytes()
    if b'Spline_Strada' not in data: continue
    target=STAGE/'Content'/path.relative_to(SRC)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,target)
    actor_count+=1
(STAGE/'Inspection.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.5','Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}),encoding='utf-8')
print('Staged',len(packages),'packages,',actor_count,'road actors and source map; source project unchanged.')
