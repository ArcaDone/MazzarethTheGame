import json,re,shutil,collections
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
SRC=Path(r'D:\UE5Projects\Comune\Content')
STAGE=ROOT/'Saved/M80BuildingResources'
files=list(SRC.rglob('*.uasset'))
rules={'intonaci_pietra_tetti':r'(^MI_.*(Stucco|Plaster|Stone_Wall|Roman_Stone|Roof_Tile|Roof_Tiles|Painted_Cracked_Concrete))','porte_finestre':r'^(SM_Door_06[ac]|SM_Door_Double_01a|SM_Slums_Window_01[af]|window_low)$','arredi':r'^(SM_Bench_01a|SM_Lamp_01a)$','vegetazione':r'^SM_.*(Olive|Palm|Oleander|Pine|Cypress)','strutture_personali':r'^(CasaFloresta|Centro|Fontana)$','cartelli':r'^(SM_Slums_Sign01b|SM_Slums_Sign02a)$'}
catalog={k:[] for k in rules}
for f in files:
    for category,pattern in rules.items():
        if re.search(pattern,f.stem,re.I):catalog[category].append('/Game/'+f.relative_to(SRC).with_suffix('').as_posix())
counts=collections.Counter(f.relative_to(SRC).parts[0] for f in files)
(ROOT/'Research/Mazzarino80/comune_resource_catalog.json').write_text(json.dumps({'source':str(SRC),'asset_count':len(files),'packages':dict(counts),'candidates':catalog},indent=2))
# A focused first set; the catalogue preserves the wider selection for later.
chosen=[]
for category,limit in [('intonaci_pietra_tetti',8),('porte_finestre',7),('arredi',2),('cartelli',2)]:
    chosen+=sorted(catalog[category])[:limit]
chosen += [p for p in catalog['intonaci_pietra_tetti'] if 'Red_Roof_Tiles' in p or 'Stucco_Facade_wfnjdgl' in p or 'Roman_Stone_Wall_tf2kaa2n' in p]
selected=set(chosen)
pending=list(chosen);missing=set();dependencies={}
while pending:
    package=pending.pop()
    path=SRC/(package[6:]+'.uasset')
    if not path.exists():missing.add(package);continue
    data=path.read_bytes()
    refs=set(x.decode('ascii') for x in re.findall(rb'/Game/[A-Za-z0-9_/]+',data))
    refs={x for x in refs if (SRC/(x[6:]+'.uasset')).exists()}
    dependencies[package]=sorted(refs)
    for ref in refs:
        if ref not in selected:selected.add(ref);pending.append(ref)
STAGE.mkdir(parents=True,exist_ok=True)
(STAGE/'Config').mkdir(exist_ok=True)
(STAGE/'Inspection.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.5','Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}))
total=0
for package in sorted(selected-missing):
    path=SRC/(package[6:]+'.uasset');target=STAGE/'Content'/(package[6:]+'.uasset')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,target);total+=path.stat().st_size
manifest={'selected':chosen,'packages':sorted(selected-missing),'missing':sorted(missing),'bytes':total,'dependencies':dependencies}
(ROOT/'Research/Mazzarino80/comune_building_resources_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'catalogued':len(files),'selected':len(chosen),'staged_dependencies':len(selected-missing),'megabytes':round(total/1048576,1),'candidates':{k:len(v) for k,v in catalog.items()}}))

