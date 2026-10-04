"""Open the isolated pilot, add the scale mannequin and render its street view."""
import json
import math
import runpy
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/PCG/CharacterPilot_1249069202.png"
REPORT = ROOT / "Saved/Mazzarino80/PCG/character_pilot_capture.json"
MAP = "/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext"

runpy.run_path(str(ROOT / "Scripts/mazzarino80_pcg_place_scale_mannequin.py"))
report = {"map": MAP, "image": str(OUT), "done": False, "error": None}
state = {"task": None, "elapsed": 0.0, "handle": None}


def tick(delta):
    try:
        state["elapsed"] += delta
        if state["task"] is not None:
            if state["task"].is_task_done():
                report["done"] = OUT.exists() and OUT.stat().st_size > 10000
                report["bytes"] = OUT.stat().st_size if OUT.exists() else 0
                REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
                unreal.unregister_slate_post_tick_callback(state["handle"])
            elif state["elapsed"] > 40:
                raise RuntimeError("Pilot render timeout")
            return
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        source = next(a for a in actors if isinstance(a, unreal.MazzarinoHistoricBuilding)
                      and a.get_editor_property("lot_id") == "1249069202")
        spline = source.get_editor_property("footprint")
        edge = source.get_editor_property("front_edge")
        count = spline.get_number_of_spline_points()
        points = [spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
                  for i in range(count)]
        a, b = points[edge], points[(edge + 1) % count]
        dx, dy = b.x - a.x, b.y - a.y
        length = math.hypot(dx, dy)
        signed = sum(p.x * points[(i + 1) % count].y - points[(i + 1) % count].x * p.y
                     for i, p in enumerate(points))
        ox, oy = ((dy / length, -dx / length) if signed > 0
                  else (-dy / length, dx / length))
        mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
        location = unreal.Vector(mx + ox * 1000, my + oy * 1000, a.z + 250)
        target = unreal.Vector(mx, my, a.z + 280)
        viewport = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        viewport.set_level_viewport_camera_info(location,
            unreal.MathLibrary.find_look_at_rotation(location, target))
        state["task"] = unreal.AutomationLibrary.take_high_res_screenshot(
            1600, 900, str(OUT), delay=.6, force_game_view=True)
        if not state["task"].is_valid_task():
            raise RuntimeError("Screenshot task unavailable")
        state["elapsed"] = 0.0
    except Exception as exc:
        report["error"] = str(exc)
        REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(state["handle"])


REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
state["handle"] = unreal.register_slate_post_tick_callback(tick)
