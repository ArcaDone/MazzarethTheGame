"""Verify the saved corridor has a continuous blocking surface."""

import json
from collections import Counter
from pathlib import Path

import unreal


root = Path(unreal.Paths.project_dir())
samples = json.loads((root / "Saved" / "Mazzarino80" / "path_audit.json").read_text())["samples"]
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == "Mazzarino80_Base"
editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = editor.get_all_level_actors()
path_actors = [a for a in actors if a.get_actor_label().startswith("M80_Provvisorio_")]
assert len(path_actors) == 32, len(path_actors)


def hit(x, y):
    result = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x * 100, y * 100, 30000),
        unreal.Vector(x * 100, y * 100, 5000),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
        unreal.DrawDebugTrace.NONE, True)
    values = result.to_tuple() if result else ()
    if values and values[0]:
        return {"actor": values[9].get_actor_label() if values[9] else None,
                "z_m": round(values[4].z / 100, 3)}
    return None


checks = []
for a, b in zip(samples, samples[1:]):
    x = (a["x_m"] + b["x_m"]) / 2
    y = (a["y_m"] + b["y_m"]) / 2
    checks.append({"s_m": round((a["s_m"] + b["s_m"]) / 2, 2),
                   "x_m": round(x, 2), "y_m": round(y, 2),
                   "hit": hit(x, y)})

result = {"path_actor_count": len(path_actors), "checks": checks,
          "hit_classes": dict(Counter(
              "path" if v["hit"] and v["hit"]["actor"].startswith("M80_Provvisorio_")
              else (v["hit"]["actor"] if v["hit"] else "miss")
              for v in checks))}
out = root / "Saved" / "Mazzarino80" / "verify_path.json"
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
unreal.log("MAZZARINO80_PATH_VERIFY " + json.dumps(result["hit_classes"]))
