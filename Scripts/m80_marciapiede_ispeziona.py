"""Why a sidewalk does not reach a house: loads the area around a house of the town (env M80_CASA = actor label, e.g.
Casa_1249044337) and, for each sidewalk within 15 m, writes its settings (magnet, reach, wall gap, width), what the
magnet did, for every spline point the distance of the paving's house-side edge from the nearest facade, and every
25 cm the real wall on both sides (traced) and how far the terrain pokes above the paving.
Out: Saved/Mazzarino80/Marciapiedi/Ispeziona/<casa>.json + <casa>.png (from above)
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_marciapiede_ispeziona.py -TimeoutMinutes 20
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Marciapiedi/Ispeziona"
CASA = os.environ.get("M80_CASA", "Casa_1249044337")
REACH = 1500.0


def cls_name(d):
    c = d.get_editor_property("native_class")
    return c.get_name() if c else ""


def seg_dist(q, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / max(dx * dx + dy * dy, 1e-6)))
    return math.hypot(q[0] - a[0] - t * dx, q[1] - a[1] - t * dy)


IGNORE = []  # the sidewalks: their own paving would stop the traces


def land_z(world, x, y, guess):
    hits = unreal.SystemLibrary.line_trace_multi(world, unreal.Vector(x, y, guess + 20000), unreal.Vector(x, y, guess - 20000),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, IGNORE, unreal.DrawDebugTrace.NONE, True)
    for h in hits or []:
        t = h.to_tuple()
        if isinstance(t[9], unreal.LandscapeProxy):
            return t[4].z
    return None


def wall_distance(world, centre, right, side, reach):
    """Horizontal distance from the spline to the first house wall on one side (None: no house within reach)."""
    end = centre + right * (side * reach)
    hits = unreal.SystemLibrary.line_trace_multi(world, centre, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, IGNORE,
                                                 unreal.DrawDebugTrace.NONE, True)
    for h in hits or []:
        t = h.to_tuple()
        if t[9]:
            return round((t[4] - centre).length(), 1), t[9].get_actor_label()
    return None


def section(world, s, half, top):
    """Every 25 cm along the sidewalk: the real wall distance on both sides, and the ground poking through the paving
    (landscape above a straight slab between its two edges, sampled every 10 cm across)."""
    path = s.get_editor_property("path")
    length = path.get_spline_length()
    rows = []
    d = 0.0
    while d <= length:
        c = path.get_location_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD)
        r = path.get_right_vector_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD)
        r = unreal.Vector(r.x, r.y, 0).normal()
        ends = [land_z(world, c.x + r.x * k * half, c.y + r.y * k * half, c.z) for k in (-1, 1)]
        row = {"m": round(d / 100, 2)}
        if None not in ends:
            worst, where = 0.0, None
            for i in range(-int(half // 10), int(half // 10) + 1):
                x = i * 10.0
                z = land_z(world, c.x + r.x * x, c.y + r.y * x, c.z)
                slab = ends[0] + (ends[1] - ends[0]) * (x + half) / (2 * half) + top
                if z is not None and z - slab > worst:
                    worst, where = z - slab, x
            row["terreno_sopra_lastra_cm"] = round(worst, 1)
            if where is not None:
                row["dove_cm_dal_centro"] = where
            eye = unreal.Vector(c.x, c.y, max(ends) + top + 60)
            row["muro_sinistra"] = wall_distance(world, eye, r, -1, half + 150)
            row["muro_destra"] = wall_distance(world, eye, r, 1, half + 150)
        rows.append(row)
        d += 25.0
    return rows


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    house_desc = [d for d in descs if str(d.get_editor_property("label")) == CASA]
    if not house_desc:
        raise RuntimeError("casa non trovata: " + CASA)
    c = m80_seq.desc_center(house_desc[0])
    area = m80_seq.near([d for d in descs if "HLOD" not in cls_name(d)], c.x, c.y, 6000.0)
    m80_seq.load(area)
    yield 120
    unreal.M80EditorLibrary.finish_all_compilation()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    house = next(a for a in actors if a.get_actor_label() == CASA)
    houses = [a for a in actors if isinstance(a, unreal.M80House) and not a.is_excluded()
              and (a.get_actor_location() - house.get_actor_location()).length() < 4000]
    facades = []
    for h in houses:
        p = [(v.x, v.y) for v in h.get_footprint_world2d()]
        facades += [(h.get_actor_label(), p[i], p[(i + 1) % len(p)]) for i in range(len(p))]
    world = m80_seq.editor_world()
    # The far-view HLOD shells are loaded in the editor too: walls and terrain as they were at the last HLOD build.
    IGNORE[:] = [a for a in actors if isinstance(a, unreal.M80Sidewalk) or "HLOD" in a.get_class().get_name()]
    at = house.get_actor_location()
    rep = {"casa": CASA, "posizione": [round(at.x), round(at.y)], "marciapiedi": []}
    for s in actors:
        if not isinstance(s, unreal.M80Sidewalk):
            continue
        path = s.get_editor_property("path")
        pts = [path.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD) for i in range(path.get_number_of_spline_points())]
        if not pts or min(seg_dist((q.x, q.y), f[1], f[2]) for q in pts for f in facades if f[0] == CASA) > REACH:
            continue
        half = s.get_editor_property("width_cm") / 2
        points = []
        for q in pts:
            label, a, b = min(facades, key=lambda f: seg_dist((q.x, q.y), f[1], f[2]))
            d = seg_dist((q.x, q.y), a, b)
            points.append({"casa_vicina": label, "centro_dal_muro_cm": round(d, 1), "bordo_dal_muro_cm": round(d - half, 1)})
        rep["marciapiedi"].append({
            "nome": s.get_actor_label(), "calamita": s.get_editor_property("snap_to_houses"),
            "portata_cm": s.get_editor_property("snap_distance_cm"), "distanza_dal_muro_cm": s.get_editor_property("wall_gap_cm"),
            "larghezza_cm": s.get_editor_property("width_cm"), "punti_agganciati": s.get_editor_property("snapped_points"),
            "stato_aggancio": s.get_editor_property("snap_status"), "altezza_cm": s.get_editor_property("top_height_cm"),
            "punti": points, "sezioni": section(world, s, half, s.get_editor_property("top_height_cm"))})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (CASA + ".json")).write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    origin, extent = house.get_actor_bounds(False)
    eye = origin + unreal.Vector(-(extent.x + 600), -(extent.y + 600), extent.z * 2 + 2500)
    cap = m80_seq.ViewCapture(1600, 900, 60.0)
    cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, origin), OUT / (CASA + ".png"))
    yield 2
    cap.destroy()


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
