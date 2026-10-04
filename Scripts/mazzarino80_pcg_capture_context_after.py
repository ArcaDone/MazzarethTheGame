"""Capture the PCG replacement from the exact baseline camera."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
camera = json.loads((root / 'Saved/Mazzarino80/PCG/context_camera_before.json').read_text(encoding='utf-8'))
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    unreal.Vector(*camera['location']), unreal.Rotator(
        pitch=camera['rotation'][0], yaw=camera['rotation'][1], roll=camera['rotation'][2]))
unreal.SystemLibrary.execute_console_command(unreal.EditorLevelLibrary.get_editor_world(), 'HighResShot 1920x1080')
