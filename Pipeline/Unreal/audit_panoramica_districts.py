"""Read-only inventory for a staged PCG city preview."""
from collections import Counter
from pathlib import Path
import json
import os
import unreal

root = Path(unreal.Paths.project_dir())
level = os.environ.get("M80_AUDIT_MAP", "/Game/Levels/Mazzarino80_Panoramica")
world = unreal.EditorLoadingAndSavingUtils.load_map(level)
if not world or world.get_name() != level.rsplit("/", 1)[-1]:
    raise RuntimeError("Cannot load requested map")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
classes = Counter(a.get_class().get_name() for a in actors)
folders = Counter(str(a.get_folder_path()) for a in actors)
buildings = {}
for a in actors:
    if isinstance(a, unreal.MazzarinoBuilding):
        lot = str(a.get_editor_property("building_id"))
        p = a.get_actor_location()
        buildings[lot] = {"label": a.get_actor_label(),
                          "folder": str(a.get_folder_path()),
                          "position_cm": [p.x, p.y, p.z],
                          "hidden_in_game": bool(a.get_editor_property("hidden"))}
out = {"map": level, "actor_count": len(actors),
       "classes": classes, "folders": folders,
       "building_count": len(buildings), "buildings": buildings}
dest = root / ("Pipeline/Unreal/panoramica_district_audit.json" if
               level.endswith("Mazzarino80_Panoramica") else
               "Pipeline/Unreal/sample_district_audit.json")
dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
print("M80_PANORAMICA_AUDIT", len(actors), len(buildings))
