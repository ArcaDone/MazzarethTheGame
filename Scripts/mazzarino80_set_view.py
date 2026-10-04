"""Set a useful overview camera in the open Mazzarino map."""

import json
from pathlib import Path
import unreal

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
before = editor.get_level_viewport_camera_info()
editor.set_level_viewport_camera_info(
    unreal.Vector(65000, 9000, 230000),
    unreal.Rotator(roll=0, pitch=-90, yaw=0))
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).set_selected_level_actors([])
after = editor.get_level_viewport_camera_info()

def vec(v):
    return [v.x, v.y, v.z]

result = {"before": [vec(before[0]), [before[1].pitch, before[1].yaw, before[1].roll]],
          "after": [vec(after[0]), [after[1].pitch, after[1].yaw, after[1].roll]]}
Path(r"D:\UE5Projects\GameAnimationSample\Saved\Mazzarino80\view_camera.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8")
unreal.log("M80_VIEW " + json.dumps(result))
