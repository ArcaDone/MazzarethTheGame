"""Repeatable performance capture for a Mazzarino80 map.

Opens the map, moves the editor viewport through fixed viewpoints and records
each one with the CSV profiler, then counts scene primitives and quits.

Environment variables:
  M80_PROFILE_MAP     map package (default: the 18-house sample)
  M80_PROFILE_OUT     output json, relative to the project (default below)
  M80_PROFILE_FRAMES  frames captured per viewpoint (default 300)
"""
import glob
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_PROFILE_MAP", "/Game/Levels/Mazzarino80_CaseStoriche_Campione")
OUT = ROOT / os.environ.get("M80_PROFILE_OUT", "Saved/Mazzarino80/Profile/profile_baseline.json")
FRAMES = int(os.environ.get("M80_PROFILE_FRAMES", "300"))
CATALOG = ROOT / "Research/Mazzarino80/PCG/Buildings_Test18.json"
STREET_LOTS = ("1249069200", "1249069228", "1249068307")
CSV_DIR = ROOT / "Saved/Profiling/CSV"


def look_at(eye, target):
    d = [t - e for t, e in zip(target, eye)]
    yaw = math.degrees(math.atan2(d[1], d[0]))
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return unreal.Vector(*eye), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)


def viewpoints():
    lots = {b["building_id"]: b for b in json.loads(CATALOG.read_text(encoding="utf-8"))["buildings"]}
    pts = [p for b in lots.values() for p in b["footprint_world_cm"]]
    cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    cz = sum(p[2] for p in pts) / len(pts)
    views = [("Overview", *look_at((cx - 9000, cy, cz + 7000), (cx, cy, cz)))]
    for lot in STREET_LOTS:
        b = lots[lot]
        poly = b["footprint_world_cm"]
        i = b["front_edge"]
        a, c = poly[i], poly[(i + 1) % len(poly)]
        mx, my = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
        ex, ey = c[0] - a[0], c[1] - a[1]
        n = math.hypot(ex, ey) or 1.0
        px, py = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
        ox, oy = -ey / n, ex / n
        if (mx - px) * ox + (my - py) * oy < 0:
            ox, oy = -ox, -oy
        z = a[2]
        views.append(("Street_" + lot, *look_at((mx + ox * 700, my + oy * 700, z + 170), (mx, my, z + 350))))
    return views


def house_viewpoints():
    """Views derived from the AM80House actors of the open map: one high overview, three streets."""
    houses = unreal.GameplayStatics.get_all_actors_of_class(m80_seq.editor_world(), unreal.M80House)
    if not houses:
        return viewpoints()
    locs = [h.get_actor_location() for h in houses]
    cx = sum(l.x for l in locs) / len(locs)
    cy = sum(l.y for l in locs) / len(locs)
    cz = sum(l.z for l in locs) / len(locs)
    span = max(max(abs(l.x - cx), abs(l.y - cy)) for l in locs)
    views = [("Overview", *look_at((cx - span * 1.1, cy - span * 0.4, cz + span * 0.8), (cx, cy, cz)))]
    ordered = sorted(houses, key=lambda h: (h.get_actor_location().x - cx) ** 2 + (h.get_actor_location().y - cy) ** 2)
    for h in ordered[:: max(1, len(ordered) // 3)][:3]:
        fp = h.get_footprint_world2d() if hasattr(h, "get_footprint_world2d") else h.get_footprint_world_2d()
        poly = [(q.x, q.y) for q in fp]
        i = h.get_editor_property("resolved_front_edge") % len(poly)
        a, c = poly[i], poly[(i + 1) % len(poly)]
        n = math.hypot(c[0] - a[0], c[1] - a[1]) or 1.0
        mx, my = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
        ox, oy = (c[1] - a[1]) / n, -(c[0] - a[0]) / n
        z = h.get_actor_location().z
        # Look along the street, the most demanding view at player height.
        tx, ty = (c[0] - a[0]) / n, (c[1] - a[1]) / n
        views.append(("Street_" + h.get_editor_property("lot_id"),
                      *look_at((mx + ox * 300 - tx * 900, my + oy * 300 - ty * 900, z + 170), (mx + tx * 1500, my + ty * 1500, z + 300))))
    return views


def scene_counts():
    counts = {"actors": 0, "ism_components": 0, "instances": 0, "static_mesh_components": 0,
              "procedural_mesh_components": 0, "dynamic_mesh_components": 0, "dynamic_mesh_triangles": 0}
    for actor in unreal.GameplayStatics.get_all_actors_of_class(m80_seq.editor_world(), unreal.Actor):
        counts["actors"] += 1
        for comp in actor.get_components_by_class(unreal.PrimitiveComponent):
            if not comp.is_visible():
                continue
            if isinstance(comp, unreal.InstancedStaticMeshComponent):
                counts["ism_components"] += 1
                counts["instances"] += comp.get_instance_count()
            elif isinstance(comp, unreal.StaticMeshComponent):
                counts["static_mesh_components"] += 1
            elif isinstance(comp, unreal.ProceduralMeshComponent):
                counts["procedural_mesh_components"] += 1
            elif isinstance(comp, unreal.DynamicMeshComponent):
                counts["dynamic_mesh_components"] += 1
                counts["dynamic_mesh_triangles"] += comp.get_dynamic_mesh().get_triangle_count()
    return counts


def summarize(csv_path):
    """Average and 95th percentile of the main columns of one CSV capture."""
    lines = Path(csv_path).read_text(encoding="utf-8", errors="ignore").splitlines()
    header = lines[0].split(",")
    rows = [line.split(",") for line in lines[1:] if line and not line.startswith("[")]
    wanted = {"FrameTime": "frame_ms", "GameThreadTime": "game_ms", "RenderThreadTime": "render_ms", "GPUTime": "gpu_ms",
              "RHI/DrawCalls": "draw_calls", "RHI/PrimitivesDrawn": "primitives"}
    out = {"frames": len(rows)}
    for column, key in wanted.items():
        if column not in header:
            continue
        i = header.index(column)
        vals = []
        for r in rows:
            try:
                vals.append(float(r[i]))
            except (IndexError, ValueError):
                pass
        if vals:
            vals.sort()
            out[key] = round(sum(vals) / len(vals), 2)
            out[key + "_p95"] = round(vals[max(0, int(len(vals) * 0.95) - 1)], 2)
    return out


def run():
    result = {"map": MAP, "frames_per_view": FRAMES, "views": {}}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    m80_seq.console("t.MaxFPS 0")
    m80_seq.console("r.VSync 0")
    result["counts"] = scene_counts()
    views = house_viewpoints() if os.environ.get("M80_PROFILE_HOUSE_VIEWS") == "1" else viewpoints()
    for name, loc, rot in views:
        m80_seq.set_view(loc, rot)
        yield 120
        before = set(glob.glob(str(CSV_DIR / "*.csv")))
        m80_seq.console("csvprofile start")
        yield FRAMES
        m80_seq.console("csvprofile stop")
        yield 30
        new = [p for p in glob.glob(str(CSV_DIR / "*.csv")) if p not in before]
        result["views"][name] = summarize(max(new, key=os.path.getmtime)) if new else {"error": "no csv"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
