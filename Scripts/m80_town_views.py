"""Viewpoints in the town map shared by the atmosphere scripts: centre of town, ground height, a shot along the Corso."""
import json
import math
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
PLAN = ROOT / "Research/Mazzarino80/building_footprint_plan.json"
STREETS = ROOT / "Research/Mazzarino80/streets_world.json"
CORSO = (61754, 11552)


def town_centre():
    lots = json.loads(PLAN.read_text(encoding="utf-8"))
    zs = sorted(l["center_cm"][2] for l in lots)
    return unreal.Vector(CORSO[0], CORSO[1], zs[len(zs) // 2])



def ground(world, x, y):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 60000), unreal.Vector(x, y, -60000),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    hit = hit[1] if isinstance(hit, tuple) else hit
    f = hit.to_tuple() if hit else None
    return f[5].z if f and f[0] else None



def corso_shot(world, c):
    """A point on the Corso near the centre, looking along the street (eye at 1.4 m)."""
    streets = json.loads(STREETS.read_text(encoding="utf-8"))["streets"]
    best = None
    for st in streets:
        if "Corso" not in (st.get("name") or ""):
            continue
        pts = st["points_cm"]
        for a, b in zip(pts, pts[1:]):
            d = math.hypot(a[0] - c.x, a[1] - c.y)
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 1500 and (best is None or d < best[0]):
                best = (d, a, b)
    if not best:
        return None
    _, a, b = best
    z = ground(world, a[0], a[1])
    if z is None:
        return None
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    return unreal.Vector(a[0], a[1], z + 140), unreal.Vector(a[0] + dx / n * 4000, a[1] + dy / n * 4000, z + 260)
