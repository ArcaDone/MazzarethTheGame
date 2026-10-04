"""Add a playable start and daylight to the provisional town overview."""

import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == "Mazzarino80_Panoramica"

location = unreal.Vector(82000, -6340, 50000)
result = unreal.SystemLibrary.line_trace_single(
    world, location, unreal.Vector(location.x, location.y, -10000),
    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
    unreal.DrawDebugTrace.NONE, True)
values = result.to_tuple() if result else ()
if not values or not values[0]:
    raise RuntimeError("No blocking ground at the proposed start")
ground = values[4]
player = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.PlayerStart,
    unreal.Vector(location.x, location.y, ground.z + 120),
    unreal.Rotator(roll=0, pitch=0, yaw=25))
player.set_actor_label("M80_Inizio_percorso")

atmosphere = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
atmosphere.set_actor_label("M80_Atmosfera")

unreal.EditorLevelLibrary.save_current_level()
report = {"world": world.get_name(), "ground_actor": values[9].get_actor_label(),
          "ground_cm": ground.z, "start_cm": [location.x, location.y, ground.z + 120]}
(root / "Saved" / "Mazzarino80" / "overview_player_start.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8")
unreal.log("M80_OVERVIEW_FINISH " + json.dumps(report))
