"""Install the isolated source assets and the compiled editor module."""
import json,shutil
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
source=ROOT/'Saved/M80ComuneInspection/Content/Mazzarino80/RoadSource'
target=ROOT/'Content/Mazzarino80/RoadSource'
shutil.copytree(source,target,dirs_exist_ok=True)
built=ROOT/'Saved/M80RoadPluginBuild/Binaries/Win64'
plugin=ROOT/'Plugins/MazzarinoRoads/Binaries/Win64'
plugin.mkdir(parents=True,exist_ok=True)
for name in ['UnrealEditor-MazzarinoRoads.dll','UnrealEditor-MazzarinoRoads.pdb','UnrealEditor.modules']:
    shutil.copy2(built/name,plugin/name)
# Make the newly compiled module discoverable to the already running editor.
modules=ROOT/'Binaries/Win64/UnrealEditor.modules'
manifest=json.loads(modules.read_text())
new_manifest=json.loads((built/'UnrealEditor.modules').read_text())
assert manifest['BuildId']==new_manifest['BuildId'], 'Different engine binary build'
backup=ROOT/'Saved/Mazzarino80/Backups/2026-09-28'
backup.mkdir(parents=True,exist_ok=True)
if not (backup/'UnrealEditor.modules').exists():shutil.copy2(modules,backup/'UnrealEditor.modules')
manifest['Modules']['MazzarinoRoads']='UnrealEditor-MazzarinoRoads.dll'
shutil.copy2(built/'UnrealEditor-MazzarinoRoads.dll',modules.parent/'UnrealEditor-MazzarinoRoads.dll')
modules.write_text(json.dumps(manifest,indent=2))
mapfile=ROOT/'Content/Levels/Mazzarino80_Panoramica.umap'
if not (backup/mapfile.name).exists():shutil.copy2(mapfile,backup/mapfile.name)
print('Source copies and road module installed; overview map backup created.')
