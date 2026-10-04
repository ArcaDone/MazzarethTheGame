import json,shutil
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
project=ROOT/'MazzarethTheGame.uproject'
backup=ROOT/'Saved/Mazzarino80/Backups/2026-09-28/MazzarethTheGame.uproject'
if not backup.exists():shutil.copy2(project,backup)
data=json.loads(project.read_text(encoding='utf-8-sig'))
for name in ['MazzarinoRoads','PythonScriptPlugin','EditorScriptingUtilities']:
    entry=next((p for p in data['Plugins'] if p['Name']==name),None)
    if entry:entry['Enabled']=True
    else:data['Plugins'].append({'Name':name,'Enabled':True})
project.write_text(json.dumps(data,indent=2),encoding='utf-8')
print('Roads and editor scripting enabled for next launch.')
