"""Bakes every AM80House of a map into Nanite static meshes, saves, and captures views.

Baked meshes go to /Game/Mazzarino80/Houses/Baked/<MapName> (derived data, gitignored).
World Partition maps (the town, L_M80_Paese_WP) are baked tile by tile (300 m): each tile is loaded,
its unbaked houses baked, the changed actor files saved and the tile unloaded, so memory stays low.
Env: M80_BAKE_MAP (default the town map), M80_BAKE_CAPTURE=0 skips captures (always skipped on the town),
     M80_BAKE_LIMIT bakes at most N houses per run (the ones not baked yet; "remaining" in the report).
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
MAP = os.environ.get("M80_BAKE_MAP", m80_seq.TOWN_MAP)
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


def bake_by_tiles(world, descs, report):
    t0 = time.time()
    baked, failed, remaining = 0, [], 0
    for tile in m80_seq.tiles(descs):
        if LIMIT and baked >= LIMIT:
            remaining += len(tile)  # upper bound: not checked
            continue
        m80_seq.load(tile)
        yield 5
        houses = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House))  # only this tile is loaded
        todo = [h for h in houses if not h.is_baked() and not h.is_excluded()]
        for i, house in enumerate(todo):
            if LIMIT and baked >= LIMIT:
                remaining += len(todo) - i
                break
            if unreal.M80EditorLibrary.bake_house(house, FOLDER, True):
                baked += 1
            else:
                failed.append(house.get_editor_property("lot_id"))
            if i % 10 == 9:
                yield 1
        if todo:
            unreal.EditorAssetLibrary.save_directory(FOLDER, only_if_is_dirty=True, recursive=True)
            m80_seq.save_all()
        m80_seq.unload(tile)
        unreal.SystemLibrary.collect_garbage()
        yield 2
    report.update({"baked": baked, "failed": failed, "remaining": remaining, "bake_seconds": round(time.time() - t0, 1)})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def run():
    report = {"map": MAP, "folder": FOLDER}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Wrong map open: " + world.get_path_name())
    descs = m80_seq.actor_descs("M80House")
    if descs:
        yield from bake_by_tiles(world, descs, report)
        return
    houses = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House))
    # Only houses that are not baked yet (or changed since); at most LIMIT per run: a few thousand Nanite
    # builds in one editor session run out of memory, so a whole town is baked by running until remaining = 0.
    todo = [h for h in houses if not h.is_baked() and not h.is_excluded()]
    t0 = time.time()
    baked = 0
    for i, house in enumerate(todo if os.environ.get("M80_BAKE_SKIP") != "1" else []):
        if LIMIT and baked >= LIMIT:
            break
        if unreal.M80EditorLibrary.bake_house(house, FOLDER, True):
            baked += 1
        if i % 10 == 9:
            unreal.SystemLibrary.collect_garbage()
            yield 1
    report["baked"] = baked
    report["remaining"] = max(0, len(todo) - baked)
    report["bake_seconds"] = round(time.time() - t0, 1)
    unreal.EditorAssetLibrary.save_directory(FOLDER, only_if_is_dirty=True, recursive=True)
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    # Report right after the save: a big town can exhaust the memory afterwards.
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not CAPTURE:
        return
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
