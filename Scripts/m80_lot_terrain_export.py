"""Terrain and footprint of one OSM lot for modelling it in Blender.

Samples the landscape height (only the terrain: houses, walls and props are ignored) on a grid around
the lot and writes the lot's spline points as they are in the map, so the Blender model sits exactly on
the ground of the game. Env: M80_LOT (lot id, default 1249067196 = Palazzo Bartoli/Branciforti),
M80_LOT_MARGIN_M (25), M80_LOT_STEP_M (1).
Output: Research/Mazzarino80/Blender/Lots/<lot>_terrain.json (world cm: x, y, z grid + footprint).
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
LOT = os.environ.get("M80_LOT", "1249067196")
MARGIN = float(os.environ.get("M80_LOT_MARGIN_M", "25")) * 100
STEP = float(os.environ.get("M80_LOT_STEP_M", "1")) * 100
OUT = ROOT / "Research/Mazzarino80/Blender/Lots" / (LOT + "_terrain.json")


def ground(world, x, y):
    hits = unreal.SystemLibrary.line_trace_multi_for_objects(
        world, unreal.Vector(x, y, 60000), unreal.Vector(x, y, -20000),
        [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1], True, [], unreal.DrawDebugTrace.NONE, True)
    for h in hits or []:
        f = h.to_tuple()
        if isinstance(f[9], unreal.LandscapeProxy):
            return f[5].z
    return None


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 20
    world = m80_seq.editor_world()
    houses = m80_seq.actor_descs("M80House")
    m80_seq.load(houses)
    yield 10
    house = None
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House):
        if a.get_editor_property("lot_id") == LOT:
            house = a
    spline = house.get_editor_property("footprint")
    pts = [spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
           for i in range(spline.get_number_of_spline_points())]
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    c = house.get_actor_location()
    m80_seq.unload(houses)
    m80_seq.load(m80_seq.near(m80_seq.actor_descs("LandscapeStreamingProxy"), c.x, c.y, 60000))
    yield 10
    x0, x1 = min(xs) - MARGIN, max(xs) + MARGIN
    y0, y1 = min(ys) - MARGIN, max(ys) + MARGIN
    nx, ny = int((x1 - x0) / STEP) + 1, int((y1 - y0) / STEP) + 1
    rows = []
    for j in range(ny):
        rows.append([ground(world, x0 + i * STEP, y0 + j * STEP) for i in range(nx)])
        if j % 20 == 19:
            yield 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "lot": LOT, "label": house.get_actor_label(), "actor_location": [c.x, c.y, c.z],
        "footprint": [[p.x, p.y, p.z] for p in pts],
        "grid": {"x0": x0, "y0": y0, "step": STEP, "nx": nx, "ny": ny, "z": rows},
    }), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
