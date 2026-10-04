import json,shutil
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample');SRC=Path(r'D:\UE5Projects\Comune\Content')
plan=json.loads((ROOT/'Research/Mazzarino80/casa_floresta_dependency_plan.json').read_text())
stage=ROOT/'Saved/M80CasaFlorestaResources';stage.mkdir(exist_ok=True)
(stage/'Inspection.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.5','Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}))
for p in plan['packages']+plan['known']:
    src=SRC/(p[6:]+'.uasset');dest=stage/'Content'/(p[6:]+'.uasset');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
print('CasaFloresta copiata con dipendenze: '+str(len(plan['packages'])+len(plan['known'])))
