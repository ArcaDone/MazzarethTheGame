"""Frame the corrected Q003 PCG building from above for visual comparison."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
row = json.loads((root / "Pipeline/Unreal/first_pcg_batch_module_export.json").read_text(encoding="utf-8"))["houses"]["1249054419"]
poly = row["footprint_world_cm"]
center = unreal.Vector(sum(p[0] for p in poly) / len(poly),
                       sum(p[1] for p in poly) / len(poly),
                       min(p[2] for p in poly) + 3500)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    center, unreal.Rotator(pitch=-82, yaw=0, roll=0))
print("M80_ALIGNMENT_SAMPLE_VIEW", center)
