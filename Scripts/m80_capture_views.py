"""Close-up checks of house facades: windows and shop fronts at 2.5, 6 and 15 m (houses V3, step 8).

Env: M80_VIEWS_MAP (default the 18-house test map), M80_VIEWS_LOTS (comma separated lot ids),
     M80_VIEWS_OUT (folder under Saved/Mazzarino80).
"""
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_VIEWS_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Houses18_V2")
LOTS = os.environ.get("M80_VIEWS_LOTS", "1249069200,1249069204,1249069228,1249069275").split(",")
OUT = ROOT / "Saved/Mazzarino80" / os.environ.get("M80_VIEWS_OUT", "HousesV2/windows")
# orbit: four views from above around the house (courtyards, outside stairs, back walls)
MODE = os.environ.get("M80_VIEWS_MODE", "front")


def look_at(eye, target):
    d = [t - e for t, e in zip(target, eye)]
    yaw = math.degrees(math.atan2(d[1], d[0]))
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return unreal.Vector(*eye), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)


def ground_z(world, x, y, guess):
    houses = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House))
    result = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, guess + 30000), unreal.Vector(x, y, guess - 30000),
                                                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, houses, unreal.DrawDebugTrace.NONE, True)
    hit = result[1] if isinstance(result, tuple) else result
    fields = hit.to_tuple() if hit else None
    return fields[5].z if fields and fields[0] else guess


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Wrong map open: " + world.get_path_name())
    capture = m80_seq.ViewCapture()
    yield 400
    for house in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House):
        lot = house.get_editor_property("lot_id")
        if lot not in LOTS:
            continue
        poly = [(q.x, q.y) for q in house.get_footprint_world2d()]
        if MODE == "orbit":
            cx, cy = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
            radius = max(math.hypot(p[0] - cx, p[1] - cy) for p in poly)
            gz = ground_z(world, cx, cy, house.get_actor_location().z)
            for k in range(4):
                ang = math.radians(45 + 90 * k)
                eye = (cx + math.cos(ang) * (radius + 900), cy + math.sin(ang) * (radius + 900), gz + 1300)
                loc, rot = look_at(eye, (cx, cy, gz + 200))
                target = OUT / "{}_orbit{}.png".format(lot, k)
                capture.capture(loc, rot, target)
                yield 20
                capture.capture(loc, rot, target)
                yield 3
            continue
        i = house.get_editor_property("resolved_front_edge") % len(poly)
        a, c = poly[i], poly[(i + 1) % len(poly)]
        n = math.hypot(c[0] - a[0], c[1] - a[1]) or 1.0
        mx, my = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
        ox, oy = (c[1] - a[1]) / n, -(c[0] - a[0]) / n
        gz = ground_z(world, mx + ox * 300, my + oy * 300, house.get_actor_location().z)
        for dist, side, aim in ((250, 0.0, 200), (600, 150.0, 300), (1500, 400.0, 500)):
            eye = (mx + ox * dist + (c[0] - a[0]) / n * side, my + oy * dist + (c[1] - a[1]) / n * side, gz + 170)
            loc, rot = look_at(eye, (mx, my, gz + aim))
            target = OUT / "{}_{:04d}.png".format(lot, dist)
            capture.capture(loc, rot, target)
            yield 20
            capture.capture(loc, rot, target)
            yield 3
    capture.destroy()


m80_seq.Sequencer(run(), log_file=str(OUT / "error.txt"))
