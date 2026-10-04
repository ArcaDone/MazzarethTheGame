"""Offscreen graphical-editor smoke test for the isolated four-house QA map."""
from pathlib import Path
import json
import time

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Pipeline/Unreal/reuse_editor_capture_status.json"
LEVEL = "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_QA"
unreal.EditorPythonScriptingLibrary.set_keep_python_script_alive(True)
world = unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:
    raise RuntimeError("Could not load graphical QA map")
unreal.EditorLevelLibrary.set_level_viewport_camera_info(
    unreal.Vector(1400, -1650, 650), unreal.Rotator(-11, 90, 0))
state = {"map": LEVEL, "started": time.time(), "screenshot_requested": False,
         "finished": False}
OUT.write_text(json.dumps(state, indent=2), encoding="utf-8")
handle = None


def on_tick(delta_seconds):
    global handle
    elapsed = time.time() - state["started"]
    if elapsed >= 12 and not state["screenshot_requested"]:
        unreal.SystemLibrary.execute_console_command(world, "HighResShot 1")
        state["screenshot_requested"] = True
        state["screenshot_at_seconds"] = round(elapsed, 2)
        OUT.write_text(json.dumps(state, indent=2), encoding="utf-8")
    if elapsed >= 18:
        state["finished"] = True
        state["elapsed_seconds"] = round(elapsed, 2)
        OUT.write_text(json.dumps(state, indent=2), encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.EditorPythonScriptingLibrary.set_keep_python_script_alive(False)


handle = unreal.register_slate_post_tick_callback(on_tick)
print("M80_EDITOR_CAPTURE_SCHEDULED", LEVEL)
