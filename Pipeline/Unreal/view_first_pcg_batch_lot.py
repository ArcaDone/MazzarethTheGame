"""Position the editor camera at eye height in front of one new PCG house."""
from pathlib import Path
import json
import math
import unreal

root = Path(unreal.Paths.project_dir())
request = json.loads((root / "Pipeline/Unreal/first_batch_view_request.json").read_text(encoding="utf-8"))
lot = request["building_id"]
distance = float(request.get("distance_cm", 450))
row = json.loads((root / "Pipeline/Unreal/first_pcg_batch_module_export.json").read_text(encoding="utf-8"))["houses"][lot]
poly = row["footprint_world_cm"]
a = poly[row["front_edge"]]
b = poly[(row["front_edge"] + 1) % len(poly)]
mid = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)
cx = sum(p[0] for p in poly) / len(poly)
cy = sum(p[1] for p in poly) / len(poly)
dx, dy = mid[0] - cx, mid[1] - cy
length = math.hypot(dx, dy)
if length < 1:
    raise RuntimeError("No valid camera direction")
dx, dy = dx / length, dy / length
location = unreal.Vector(mid[0] + dx * distance, mid[1] + dy * distance,
                         min(p[2] for p in poly) + 175)
yaw = math.degrees(math.atan2(-dy, -dx))
rotation = unreal.Rotator(pitch=-4, yaw=yaw, roll=0)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(location, rotation)
report = {"lot": lot, "camera_cm": [location.x, location.y, location.z],
          "yaw": yaw, "front_edge": row["front_edge"], "floors": row["floor_count"]}
(root / "Pipeline/Unreal/first_batch_view_result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_CAMERA", report)
