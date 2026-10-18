"""Drive from the Matrice to the Madonna in the town (L_M80_Paese_WP, Play In Editor) with the Carabinieri's Alfa 155,
measuring every frame: where the frame time jumps (hitches) and what was going on then.
- Vito gets in the Alfa by the Matrice (m80_alfa155_posiziona.py), an autopilot drives it along the route of the town's
  roads (Saved/Mazzarino80/Veicoli/percorso_matrice_madonna.json) at ~35 km/h;
- every frame: real time between frames, game time, where, how fast; frames over HITCH_MS are hitches;
- "stat dumphitches" with t.HitchFrameTimeThreshold: the engine writes into the log the stats tree of each hitch frame
  (the log lines are cut out into hitch_log.txt afterwards by the caller);
- photos from the driving camera at the start, halfway and at the end.
Out: Saved/Mazzarino80/Giro/giro.json, foto_*.png
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_giro_matrice_madonna.py -ForceLit -TimeoutMinutes 40
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
OUT = ROOT / "Saved/Mazzarino80/Giro"
ROUTE = json.loads((ROOT / "Saved/Mazzarino80/Veicoli/percorso_matrice_madonna.json").read_text(encoding="utf-8"))
LABEL = "Auto_Alfa155_Carabinieri"
SPEED = float(os.environ.get("M80_GIRO_KMH", "35"))
HITCH_MS = 50.0
r = {"route_m": 0}


def save():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "giro.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


def now(world):
    return unreal.GameplayStatics.get_time_seconds(world)


def state(pc):
    return str(pc.get_editor_property("state")).split(".")[-1].split(":")[0].upper()


def shot(world, name):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1600x900")
    for _ in range(30):
        yield 1
    m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1)


# Route: cumulative distance, for the point some metres ahead of the car.
CUM = [0.0]
for a, b in zip(ROUTE, ROUTE[1:]):
    CUM.append(CUM[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
r["route_m"] = round(CUM[-1] / 100)


def along(d):
    d = max(0.0, min(d, CUM[-1]))
    for i in range(1, len(CUM)):
        if CUM[i] >= d:
            t = (d - CUM[i - 1]) / max(1e-6, CUM[i] - CUM[i - 1])
            a, b = ROUTE[i - 1], ROUTE[i]
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    return ROUTE[-1][0], ROUTE[-1][1]


def project(x, y, near):
    """Distance along the route of the point nearest to (x, y), searched around the last one (no jumping back)."""
    best, bd = near, 1e18
    d = max(0.0, near - 2000)
    while d <= min(CUM[-1], near + 4000):
        px, py = along(d)
        e = (px - x) ** 2 + (py - y) ** 2
        if e < bd:
            best, bd = d, e
        d += 100
    return best


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("foto_*.png"):
        f.unlink()
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    t_play = time.time()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 30
    world = unreal.EditorLevelLibrary.get_game_world()
    while world is None or unreal.GameplayStatics.get_player_controller(world, 0) is None or \
            unreal.GameplayStatics.get_player_controller(world, 0).get_player_character() is None:
        yield 5
        world = unreal.EditorLevelLibrary.get_game_world()
    r["play_start_s"] = round(time.time() - t_play, 1)
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    cars = [c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80CarAlfa155)]
    r["alfa_found"] = len(cars)
    if not cars:
        save()
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        return
    car = cars[0]
    # Let the town around the start come in, then get in.
    t0 = time.time()
    while time.time() - t0 < 20:
        yield 5
    walker = pc.get_player_character()
    door = car.get_actor_location() - car.get_actor_right_vector() * 220 + unreal.Vector(0, 0, 80)
    walker.set_actor_location(door, False, True)
    for _ in range(20):
        yield 1
    pc.interact()
    t0 = now(world)
    while now(world) - t0 < 12 and pc.get_controlled_pawn() != car:
        yield 1
    r["driving"] = pc.get_controlled_pawn() == car
    if not r["driving"]:
        save()
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        return
    mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    for s in shot(world, "foto_1_partenza"):
        yield s
    for cmd in ("t.HitchFrameTimeThreshold %d" % HITCH_MS, "stat dumphitches"):
        unreal.SystemLibrary.execute_console_command(world, cmd)
    frames, hitches = [], []
    d_on = 0.0
    last = time.perf_counter()
    t_start = now(world)
    stuck = 0.0
    photo_mid = False
    while now(world) - t_start < 180:
        t = time.perf_counter()
        dt_ms = (t - last) * 1000.0
        last = t
        p = car.get_actor_location()
        f = car.get_actor_forward_vector()
        kmh = car.get_speed_kmh()
        d_on = project(p.x, p.y, d_on)
        frames.append(round(dt_ms, 1))
        if dt_ms > HITCH_MS and len(frames) > 1:
            hitches.append({"t": round(now(world) - t_start, 2), "ms": round(dt_ms), "at": [round(p.x), round(p.y), round(p.z)],
                            "m": round(d_on / 100), "kmh": round(kmh)})
        if CUM[-1] - d_on < 1200:
            break
        # Pure pursuit: aim at the route 12 m ahead.
        tx, ty = along(d_on + 1200)
        dx, dy = tx - p.x, ty - p.y
        cross = f.x * dy - f.y * dx
        dot = f.x * dx + f.y * dy
        ang = math.degrees(math.atan2(cross, dot))
        car.set_cart_input(0.0, 0.0, max(-1.0, min(1.0, ang / 25.0)))
        target = SPEED * (0.6 if abs(ang) > 25 else 1.0)
        if kmh < target:
            mv.set_throttle_input(0.65)
            mv.set_brake_input(0.0)
        else:
            mv.set_throttle_input(0.0)
            mv.set_brake_input(0.25 if kmh > target + 6 else 0.0)
        stuck = stuck + dt_ms / 1000.0 if abs(kmh) < 1.5 else 0.0
        if stuck > 10:
            r["stuck_at"] = [round(p.x), round(p.y), round(d_on / 100)]
            break
        if not photo_mid and d_on > CUM[-1] / 2:
            photo_mid = True
            mv.set_throttle_input(0.0)
            for s in shot(world, "foto_2_meta"):
                yield s
            last = time.perf_counter()
        yield 1
    mv.set_throttle_input(0.0)
    mv.set_brake_input(1.0)
    unreal.SystemLibrary.execute_console_command(world, "stat dumphitches")
    r["arrived"] = CUM[-1] - d_on < 1200
    r["driven_m"] = round(d_on / 100)
    r["seconds"] = round(now(world) - t_start, 1)
    srt = sorted(frames[1:])
    if srt:
        r["frames"] = len(srt)
        r["fps_mean"] = round(1000.0 * len(srt) / sum(srt), 1)
        r["ms_median"] = srt[len(srt) // 2]
        r["ms_p95"] = srt[int(len(srt) * 0.95)]
        r["ms_p99"] = srt[int(len(srt) * 0.99)]
        r["ms_max"] = srt[-1]
    r["hitches"] = hitches
    r["hitch_count"] = len(hitches)
    save()
    for s in shot(world, "foto_3_arrivo"):
        yield s
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "errore.txt"))
