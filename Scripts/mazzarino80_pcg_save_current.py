import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
saved=unreal.EditorLevelLibrary.save_current_level()
(root/'Saved/Mazzarino80/PCG/save_current.json').write_text(json.dumps({'saved':saved,'world':str(unreal.EditorLevelLibrary.get_editor_world())},indent=2),encoding='utf-8')
