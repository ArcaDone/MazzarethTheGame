"""Probe of the area around the Madonna in the town, for "the Ape stops there and won't go on": where the Madonna,
the PlayerStart and the placed vehicles are, every actor within RADIUS of the Madonna (class, label, size), the
loaded actors' colliding components (hidden ones flagged: invisible walls) and the houses' bake state, plus two
photos from above; the profile of the Corso (the road the player drives from the Matrice up to the Madonna): ground
height every metre with slope and steps, what is hit there; and the Ape's engine, gears and mass. Nothing is saved.
Out: Saved/Mazzarino80/Madonna/sonda.json, sopra.png, obliqua.png
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_madonna_sonda.py -ForceLit
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
OUT = ROOT / "Saved/Mazzarino80/Madonna"
RADIUS = 8000.0
CORSO = "Corso Vittorio Emanuele"
ROADS_JSON = ROOT / "Research/Mazzarino80/generated/road_splines.json"
APE = "/Game/Drive/ApeCar/BP_ApeCar.BP_ApeCar_C"


def prop(obj, *names):
    for n in names:
        try:
            return obj.get_editor_property(n)
        except Exception:  # noqa: BLE001
            pass
    return None


def label(d):
    return str(prop(d, "actor_label", "label") or prop(d, "actor_name", "name") or "")


def size(d):
    b = d.get_editor_property("bounds")
    e = b.max - b.min
    return [round(e.x), round(e.y), round(e.z)]


def xyz(v):
    return [round(v.x), round(v.y), round(v.z)]


def colliders(actor):
    out = []
    for c in actor.get_components_by_class(unreal.PrimitiveComponent):
        if c.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION:
            continue
        origin, extent, _ = unreal.SystemLibrary.get_component_bounds(c)
        mesh = prop(c, "static_mesh")
        out.append({"comp": c.get_name(), "class": c.get_class().get_name(),
                    "mesh": mesh.get_name() if mesh else None,
                    "visible": bool(c.is_visible()) and not actor.is_hidden_ed(),
                    "hidden_in_game": bool(prop(c, "hidden_in_game")) or bool(prop(actor, "hidden")),
                    "profile": str(c.get_collision_profile_name()),
                    "center": xyz(origin), "extent": xyz(extent)})
    return out


def trace(world, a, b, ignore):
    hit = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                 unreal.DrawDebugTrace.NONE, True)
    if hit is None:
        return None, None
    t = hit.to_tuple()
    if not t[0]:
        return None, None
    return t[4], (t[9].get_actor_label() if t[9] else None)


def road_profile(points, ignore):
    """Ground under a road centre line (OSM points, cm) every metre, ignoring the HLOD proxies: height, slope over
    5 m, steps between samples, the actor hit; plus walls met by a ray 60 cm above the ground towards the next sample."""
    world = m80_seq.editor_world()
    rows, prev = [], None
    walked = 0.0
    for a, b in zip(points, points[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(seg // 100))
        for k in range(n):
            f = k / n
            x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            z0 = (prev["z"] if prev and prev["z"] is not None else a[2] + (b[2] - a[2]) * f)
            p, actor = trace(world, unreal.Vector(x, y, z0 + 400), unreal.Vector(x, y, z0 - 1500), ignore)
            row = {"d_m": round((walked + seg * f) / 100), "xy": [round(x), round(y)], "z": round(p.z) if p else None, "hit": actor}
            if prev and p and prev["z"] is not None:
                row["step_cm"] = round(p.z - prev["z"])
                q, wall = trace(world, unreal.Vector(prev["xy"][0], prev["xy"][1], prev["z"] + 60), unreal.Vector(x, y, p.z + 60), ignore)
                if q:
                    row["wall"] = wall
            rows.append(row)
            prev = row
        walked += seg
    for i, r in enumerate(rows):
        j = min(i + 5, len(rows) - 1)
        if j > i and r["z"] is not None and rows[j]["z"] is not None:
            r["slope_pct"] = round((rows[j]["z"] - r["z"]) / ((j - i) * 100.0) * 100, 1)
    return {"length_m": round(walked / 100), "max_slope_pct": max((abs(r.get("slope_pct", 0)) for r in rows), default=0),
            "no_ground": sum(1 for r in rows if r["z"] is None),
            "problems": [r for r in rows if abs(r.get("step_cm", 0)) > 10 or r.get("wall") or r["z"] is None], "samples": rows}


def ape_stats():
    cls = unreal.load_object(None, APE)
    if not cls:
        return "BP_ApeCar not found"
    a = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(cls, unreal.Vector(0, 0, -100000))
    out = {}
    try:
        mv = a.get_components_by_class(unreal.ChaosWheeledVehicleMovementComponent)[0]
        eng = mv.get_editor_property("engine_setup")
        out["max_torque"] = eng.get_editor_property("max_torque")
        out["max_rpm"] = eng.get_editor_property("max_rpm")
        tr = mv.get_editor_property("transmission_setup")
        out["gears"] = [round(g, 2) for g in tr.get_editor_property("forward_gear_ratios")]
        out["final_ratio"] = tr.get_editor_property("final_ratio")
        out["mass_kg"] = mv.get_editor_property("mass")
        out["wheels"] = [str(w.get_editor_property("wheel_class")) for w in mv.get_editor_property("wheel_setups")]
        for w in mv.get_editor_property("wheel_setups"):
            cdo = unreal.get_default_object(w.get_editor_property("wheel_class"))
            out.setdefault("wheel_data", []).append({k: cdo.get_editor_property(k) for k in
                                                     ("wheel_radius", "friction_force_multiplier", "max_brake_torque", "suspension_max_raise",
                                                      "suspension_max_drop", "affected_by_engine")})
    except Exception as e:  # noqa: BLE001
        out["error"] = repr(e)
    a.destroy_actor()
    return out


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    report = {}
    madonna = [d for d in descs if "madonna" in label(d).lower() or "madonna" in str(prop(d, "actor_package") or "").lower()]
    report["madonna_descs"] = [{"label": label(d), "class": str(prop(d, "native_class").get_name()), "center": xyz(m80_seq.desc_center(d)),
                                "size": size(d)} for d in madonna]
    for key, test in (("player_start", lambda d: m80_seq.desc_class_is(d, "PlayerStart")),
                      ("vehicles", lambda d: any(k in label(d).lower() for k in ("ape", "vespa", "panda", "golf", "carrett", "vehicle")))):
        report[key] = [{"label": label(d), "center": xyz(m80_seq.desc_center(d))} for d in descs if test(d)]
    corso = [r for r in json.loads(ROADS_JSON.read_text(encoding="utf-8")) if CORSO in r["name"] or "Salita Madonna" in r["name"]]
    corso_pts = [q for r in corso for q in r["points_cm"]]
    report["matrice"] = [{"label": label(d), "center": xyz(m80_seq.desc_center(d))} for d in descs if "matrice" in label(d).lower()]
    if not madonna:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "sonda.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        return
    main = max(madonna, key=lambda d: size(d)[0] * size(d)[1])
    c = m80_seq.desc_center(main)
    around = m80_seq.near(descs, c.x, c.y, RADIUS)
    report["around"] = sorted(({"label": label(d), "class": str(prop(d, "native_class").get_name()), "center": xyz(m80_seq.desc_center(d)),
                                "size": size(d), "dist_m": round(math.hypot(m80_seq.desc_center(d).x - c.x, m80_seq.desc_center(d).y - c.y) / 100)}
                               for d in around), key=lambda r: r["dist_m"])
    corridor = [d for d in descs if any(math.hypot(m80_seq.desc_center(d).x - q[0], m80_seq.desc_center(d).y - q[1]) < 4000
                                        for q in corso_pts)]
    report["corridor_actors"] = len(corridor)
    m80_seq.load(around + corridor)
    yield 150
    report["ape"] = ape_stats()
    profiles = {}
    ignore = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
              if "HLOD" in a.get_class().get_name()]
    report["hlod_ignored"] = len(ignore)
    for r in corso:
        try:
            profiles[r["name"] + " " + r["id"]] = road_profile(r["points_cm"], ignore)
        except Exception as e:  # noqa: BLE001
            profiles[r["id"]] = repr(e)
    report["profiles"] = profiles
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    loaded = []
    for a in actors:
        loc = a.get_actor_location()
        if math.hypot(loc.x - c.x, loc.y - c.y) > RADIUS:
            continue
        entry = {"label": a.get_actor_label(), "class": a.get_class().get_name(), "location": xyz(loc),
                 "colliders": colliders(a)}
        if isinstance(a, unreal.M80House):
            entry["baked"] = a.is_baked()
            entry["build_info"] = str(prop(a, "build_info"))
        loaded.append(entry)
    report["loaded"] = loaded
    cap = m80_seq.ViewCapture(1600, 1200, 70.0)
    cap.capture(unreal.Vector(c.x, c.y, c.z + 9000), unreal.Rotator(0, -90, 0), OUT / "sopra.png")
    cap.capture(unreal.Vector(c.x - 5000, c.y - 5000, c.z + 3500), unreal.Rotator(0, -28, 45), OUT / "obliqua.png")
    cap.destroy()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sonda.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    yield 5


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
