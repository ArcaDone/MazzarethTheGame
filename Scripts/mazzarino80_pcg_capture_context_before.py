"""Record the original sample camera and request a matching render."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
location,rotation=unreal.EditorLevelLibrary.get_level_viewport_camera_info()
report={'location':[location.x,location.y,location.z],
        'rotation':[rotation.pitch,rotation.yaw,rotation.roll],
        'world':str(unreal.EditorLevelLibrary.get_editor_world())}
(root/'Saved/Mazzarino80/PCG/context_camera_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.SystemLibrary.execute_console_command(unreal.EditorLevelLibrary.get_editor_world(),'HighResShot 1920x1080')
