"""Play test of the traffic test map L_M80_ProvaMatrice (made by m80_prova_matrice.py): for M80_DURATA game seconds (default
180) it records, every 5 s, every car (who drives it, speed, what its driver is doing) and the people (how many in the
middle of a roadway, how many waiting at the kerb), with photos from behind two of the moving cars and of the square.
Checks: cars move along the lanes and do not stay stuck, nobody drives onto the strips along the houses, people keep off
the middle of the roads except to cross, parked cars get taken and cars park at the end of their drive.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_prova_matrice_test.py -ForceLit -TimeoutMinutes 40
Report: Saved/Mazzarino80/ProvaMatrice/Test/traffico.json, photos there.
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
MAP = "/Game/Mazzarino80/Traffico/Maps/L_M80_ProvaMatrice"
OUT = ROOT / "Saved/Mazzarino80/ProvaMatrice/Test"
DURATA = float(os.environ.get("M80_DURATA", "180"))
V = unreal.Vector
report = {"samples": [], "shots": []}


def now(world):
    return unreal.GameplayStatics.get_time_seconds(world)


def wait(world, seconds):
    t0 = now(world)
    while now(world) - t0 < seconds:
        yield 1


def shot(world, name):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1280x720")
    yield 20
    report["shots"].append([name, bool(m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1))])


def save():
    (OUT / "traffico.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


def roads(world):
    """Centre lines (every 2 m) and half widths of the roads cars use, for 'in the middle of the roadway'."""
    out = []
    for r in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if r.get_class().get_name() != "MazzarinoRoadSpline":
            continue
        w = float(r.get_editor_property("width_meters")) * 100
        name = str(r.get_editor_property("road_name"))
        if w < 250 or any(k in name for k in ("footway", "steps", "pedestrian")):
            continue
        sp = r.get_editor_property("spline")
        n = max(1, int(sp.get_spline_length() / 200))
        pts = [sp.get_location_at_distance_along_spline(sp.get_spline_length() * i / n, unreal.SplineCoordinateSpace.WORLD) for i in range(n + 1)]
        out.append((pts, w / 2))
    return out


def in_road(p, rs, margin=110.0):
    for pts, half in rs:
        h = half - margin
        if h <= 0:
            continue
        for a, b in zip(pts, pts[1:]):
            ab = V(b.x - a.x, b.y - a.y, 0)
            l2 = ab.x * ab.x + ab.y * ab.y
            t = 0 if l2 < 1 else max(0.0, min(1.0, ((p.x - a.x) * ab.x + (p.y - a.y) * ab.y) / l2))
            if math.hypot(a.x + ab.x * t - p.x, a.y + ab.y * t - p.y) < h:
                return True
    return False


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 300
    world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    for atmo in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Atmosphere):
        atmo.set_editor_property("bAdvanceInGame", False)
        atmo.set_hour(11.0)
    traffic = unreal.M80Traffico.trova(world)
    report["lanes"] = traffic.descrivi()
    rs = roads(world)
    start = now(world)
    last = {}
    moved = {}
    shots = 0
    kerb_shots = 0
    while now(world) - start < DURATA:
        for s in wait(world, 5):
            yield s
        cars = []
        for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car):
            ctrl = c.get_controller()
            p = c.get_actor_location()
            key = c.get_actor_label()
            if key in last:
                moved[key] = moved.get(key, 0.0) + math.hypot(p.x - last[key].x, p.y - last[key].y) / 100.0
            last[key] = p
            diario = ctrl.get_editor_property("diario") if ctrl and ctrl.get_class().get_name() == "M80AutistaAI" else ""
            cars.append([key, round(c.get_speed_kmh(), 1), ctrl.get_class().get_name() if ctrl else "", diario])
        people = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Pedone))
        on_road = sum(1 for a in people if a.get_attach_parent_actor() is None and in_road(a.get_actor_location(), rs))
        kerb = sum(1 for a in people if a.get_controller() and a.get_controller().get_class().get_name() == "M80PedoneAI" and a.get_controller().is_at_kerb())
        states = {}
        for a in people:
            st = getattr(a.get_editor_property("stato"), "name", str(a.get_editor_property("stato")))
            states[st] = states.get(st, 0) + 1
        report["samples"].append({"t": round(now(world) - start), "cars": cars, "people": len(people), "in_road_middle": on_road,
                                  "at_kerb": kerb, "states": states})
        # Photos from behind a moving driven car, now and then.
        driven = [c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car)
                  if c.get_controller() and c.get_controller().get_class().get_name() == "M80AutistaAI" and c.get_speed_kmh() > 5]
        if driven and shots < 6 and int(now(world) - start) % 30 < 5:
            c = driven[shots % len(driven)]
            # The car's own chase camera.
            pc.set_view_target_with_blend(c, 0.0)
            yield 3
            for s in shot(world, "auto_%d" % shots):
                yield s
            shots += 1
        # Someone waiting at the kerb for a car to pass: the player steps behind them, a photo.
        waiting = [a for a in people if a.get_controller() and a.get_controller().get_class().get_name() == "M80PedoneAI"
                   and a.get_controller().is_at_kerb()]
        if waiting and kerb_shots < 4:
            a = waiting[kerb_shots % len(waiting)]
            pawn = pc.get_controlled_pawn()
            back = a.get_actor_location() - a.get_actor_forward_vector() * 380 + V(0, 0, 60)
            rot = unreal.MathLibrary.find_look_at_rotation(back, a.get_actor_location() + a.get_actor_forward_vector() * 600)
            pawn.set_actor_location_and_rotation(back, unreal.Rotator(0, 0, rot.yaw), False, True)
            pc.set_control_rotation(unreal.Rotator(-8, 0, rot.yaw))
            pc.set_view_target_with_blend(pawn, 0.0)
            yield 4
            for s_ in shot(world, "attraversa_%d" % kerb_shots):
                yield s_
            kerb_shots += 1
        save()
    report["moved_m"] = {k: round(v) for k, v in moved.items()}
    report["spots"] = [[s.get_actor_label(), bool(any(math.hypot(c.get_actor_location().x - s.get_actor_location().x,
                                                                c.get_actor_location().y - s.get_actor_location().y) < 300
                                                     for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car)))]
                       for s in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Parcheggio)]
    # Back to the player in the square, looking about.
    pc.set_view_target_with_blend(pc.get_controlled_pawn(), 0.0)
    yield 5
    for s_ in shot(world, "piazza"):
        yield s_
    save()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
