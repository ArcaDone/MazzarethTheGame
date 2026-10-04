import json
from pathlib import Path
import unreal

target = '/Game/Levels/Mazzarino80_CaseStoriche_Campione'
ok = unreal.EditorLevelLibrary.load_level(target)
Path(unreal.Paths.project_dir(),'Saved/Mazzarino80/PCG/open_sample.json').write_text(
    json.dumps({'target':target,'loaded':ok},indent=2),encoding='utf-8')
