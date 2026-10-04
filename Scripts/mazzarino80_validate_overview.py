"""Check imported town meshes and terrain collision in the open overview level."""

import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == "Mazzarino80_Panoramica", world.get_name()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()

def hit(x, y):
    result = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, 50000), unreal.Vector(x, y, -10000),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
        unreal.DrawDebugTrace.NONE, True)
    values = result.to_tuple() if result else ()
    if not values or not values[0]:
        return None
    return {"actor": values[9].get_actor_label() if values[9] else None,
            "z_cm": values[4].z}

points = [(84225, -5455), (82000, -6340), (81974, -6255),
          (85000, -5500), (88000, -4600),
          (82374, -4006), (65000, 9000), (30000, -25000),
          (100000, 30000), (0, 50000), (125000, -20000)]
result = {"world": world.get_name(),
          "actors": [a.get_actor_label() for a in actors],
          "traces": [{"x_cm": x, "y_cm": y, "hit": hit(x, y)} for x, y in points]}
(root / "Saved" / "Mazzarino80" / "overview_validation.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8")
unreal.log("M80_OVERVIEW_VALIDATE " + json.dumps(result))
