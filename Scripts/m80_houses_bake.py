"""Bakes every AM80House of a map into Nanite static meshes, saves, and captures views.

Baked meshes go to /Game/Mazzarino80/Houses/Baked/<MapName> (derived data, gitignored).
Env: M80_BAKE_MAP (default the 18-house test map), M80_BAKE_CAPTURE=0 skips captures,
     M80_BAKE_LIMIT bakes only the first N houses (for quick tests).
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_BAKE_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Houses18_V2")
MAP_NAME = MAP.rsplit("/", 1)[-1]
FOLDER = "/Game/Mazzarino80/Houses/Baked/" + MAP_NAME
OUT = ROOT / "Saved/Mazzarino80/HousesV2" / ("bake_" + MAP_NAME)
LIMIT = int(os.environ.get("M80_BAKE_LIMIT", "0"))
CAPTURE = os.environ.get("M80_BAKE_CAPTURE", "1") != "0"


def look_at(eye, target):
    d = [t - e for t, e in zip(target, eye)]
    yaw = math.degrees(math.atan2(d[1], d[0]))
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return unreal.Vector(*eye), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)


def ground_z(world, x, y, guess):
    """Height of whatever is below (x, y): the landscape or a road, never a house."""
    houses = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House))
    result = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, guess + 30000), unreal.Vector(x, y, guess - 30000),
                                                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, houses, unreal.DrawDebugTrace.NONE, True)
    hit = result[1] if isinstance(result, tuple) else result
    fields = hit.to_tuple() if hit else None
    return fields[5].z if fields and fields[0] else guess


def street_view(world, house):
    """Camera in front of the main facade, pulled back until it would hit the opposite wall."""
    fp = house.get_footprint_world2d() if hasattr(house, "get_footprint_world2d") else house.get_footprint_world_2d()
    poly = [(q.x, q.y) for q in fp]
    i = house.get_editor_property("resolved_front_edge") % len(poly)
    a, c = poly[i], poly[(i + 1) % len(poly)]
    n = math.hypot(c[0] - a[0], c[1] - a[1]) or 1.0
    mx, my = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
    ox, oy = (c[1] - a[1]) / n, -(c[0] - a[0]) / n
    z = ground_z(world, mx + ox * 300, my + oy * 300, house.get_actor_location().z) + 170
    start = unreal.Vector(mx + ox * 60, my + oy * 60, z)
    end = unreal.Vector(mx + ox * 1200, my + oy * 1200, z)
    result = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                                    unreal.DrawDebugTrace.NONE, True)
    hit = result[1] if isinstance(result, tuple) else result
    dist = 1200
    fields = hit.to_tuple() if hit else None
    if fields and fields[0]:  # (blocking_hit, initial_overlap, time, distance, ...)
        dist = max(250, fields[3] + 60 - 80)
    eye = (mx + ox * dist, my + oy * dist, z)
    return look_at(eye, (mx, my, z + 250))


def run():
    report = {"map": MAP, "folder": FOLDER}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Wrong map open: " + world.get_path_name())
    houses = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House))
    if LIMIT:
        houses = houses[:LIMIT]
    t0 = time.time()
    baked = 0
    for i, house in enumerate(houses if os.environ.get("M80_BAKE_SKIP") != "1" else []):
        if unreal.M80EditorLibrary.bake_house(house, FOLDER, True):
            baked += 1
        if i % 10 == 9:
            unreal.SystemLibrary.collect_garbage()
            yield 1
    report["baked"] = baked
    report["bake_seconds"] = round(time.time() - t0, 1)
    unreal.EditorAssetLibrary.save_directory(FOLDER, only_if_is_dirty=False, recursive=True)
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 60
    if CAPTURE:
        capture = m80_seq.ViewCapture()
        yield 400  # distance fields and Lumen cards build asynchronously
        for house in houses[:40]:
            loc, rot = street_view(world, house)
            target = OUT / ("Street_" + house.get_editor_property("lot_id") + ".png")
            capture.capture(loc, rot, target)
            yield 20
            capture.capture(loc, rot, target)
            yield 3
        # Views from above the street: terraces, set-back and unfinished floors, antennas.
        for house in houses[:40]:
            loc, rot = street_view(world, house)
            c = house.get_actor_location()
            eye = (loc.x + (loc.x - c.x) * 0.6, loc.y + (loc.y - c.y) * 0.6, c.z + 1500)
            loc, rot = look_at(eye, (c.x, c.y, c.z + 500))
            target = OUT / ("Roof_" + house.get_editor_property("lot_id") + ".png")
            capture.capture(loc, rot, target)
            yield 20
            capture.capture(loc, rot, target)
            yield 3
        capture.destroy()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT / "error.txt"))
