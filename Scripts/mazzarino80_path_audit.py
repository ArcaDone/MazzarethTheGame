"""Sample collision on the candidate Matrice–San Domenico corridor."""

import json
import math
from pathlib import Path

import unreal


waypoints = [(820.78, -68.35), (870.25, -47.35),
             (917.74, -26.71), (949.73, -7.54)]
out = Path(unreal.Paths.project_dir()) / "Saved" / "Mazzarino80" / "path_audit.json"
out.parent.mkdir(parents=True, exist_ok=True)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
ignore_for_landscape = [
    actor for actor in actors
    if not actor.get_class().get_name().startswith("Landscape")
]


def trace(x, y, ignored):
    result = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x * 100, y * 100, 30000),
        unreal.Vector(x * 100, y * 100, 5000),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignored,
        unreal.DrawDebugTrace.NONE, True)
    values = result.to_tuple() if result else ()
    if not values or not values[0]:
        return None
    return {"z_m": round(values[4].z / 100, 3),
            "actor": values[9].get_actor_label() if values[9] else None}


samples = []
distance = 0.0
for a, b in zip(waypoints, waypoints[1:]):
    length = math.dist(a, b)
    count = math.ceil(length / 5)
    for i in range(count):
        t = i / count
        x = a[0] + (b[0] - a[0]) * t
        y = a[1] + (b[1] - a[1]) * t
        samples.append({"s_m": round(distance + length * t, 2),
                        "x_m": round(x, 2), "y_m": round(y, 2),
                        "ground": trace(x, y, ignore_for_landscape),
                        "top_hit": trace(x, y, [])})
    distance += length
samples.append({"s_m": round(distance, 2), "x_m": waypoints[-1][0],
                "y_m": waypoints[-1][1],
                "ground": trace(*waypoints[-1], ignore_for_landscape),
                "top_hit": trace(*waypoints[-1], [])})

out.write_text(json.dumps({"waypoints": waypoints, "samples": samples}, indent=2),
               encoding="utf-8")
unreal.log("MAZZARINO80_PATH_AUDIT " + str(out))
