"""Automatic test drive in the test level (Play In Editor), to tune the cars with numbers.

For each drivable car on the start line: full throttle for ACCEL_S seconds (times to 30/50/80 km/h,
top speed, gear), then a full-lock turn at speed (max roll, tipped over or not), then full brake
(stopping distance). Report: Saved/Mazzarino80/Vehicles/telemetry.json.
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
MAP = "/Game/Mazzarino80/Vehicles/L_M80_ProvaGuida"
OUT = ROOT / "Saved/Mazzarino80/Vehicles" / ("telemetry%s.json" % ("_" + os.environ["M80_TEL_ONLY"] if os.environ.get("M80_TEL_ONLY") else ""))
ACCEL_S = float(os.environ.get("M80_TEL_ACCEL_S", "30"))
TURN_KMH = float(os.environ.get("M80_TEL_TURN_KMH", "40"))
STEER = float(os.environ.get("M80_TEL_STEER", "0.5"))


def game_world():
    return unreal.EditorLevelLibrary.get_game_world()


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 300
    world = game_world()
    if not world:
        raise RuntimeError("PIE did not start")
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    if pc:
        pc.un_possess()  # the script drives; the player car would override steering
    cars = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car))
    only = os.environ.get("M80_TEL_ONLY")
    if only:
        for c in cars:
            if only not in c.get_name():
                c.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent).set_handbrake_input(True)
        cars = [c for c in cars if only in c.get_name()]
    data = {}
    for c in cars:
        data[c.get_name()] = {"name": str(c.get_editor_property("display_name")), "samples": [], "start": c.get_actor_location()}
    clock = unreal.GameplayStatics.get_time_seconds

    def mv(c):
        return c.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)

    def sample(phase):
        t = clock(world)
        for c in cars:
            up = c.get_actor_up_vector()
            p = c.get_actor_location()
            data[c.get_name()]["samples"].append([phase, round(t, 2), round(c.get_speed_kmh(), 1), c.get_gear(), round(c.get_engine_rpm()),
                                                  round(math.degrees(math.asin(max(-1, min(1, c.get_actor_right_vector().z)))), 1), round(up.z, 3),
                                                  round(p.x), round(p.y), round(p.z),
                                                  round(math.degrees(math.asin(max(-1, min(1, c.get_actor_forward_vector().z)))), 1)])

    # Phase 1: full throttle.
    t0 = clock(world)
    for c in cars:
        mv(c).set_requires_controller_for_inputs(False)  # nobody possesses them during the test
        mv(c).set_handbrake_input(False)
        mv(c).set_brake_input(0.0)
        mv(c).set_throttle_input(1.0)
    while clock(world) - t0 < ACCEL_S:
        for c in cars:
            mv(c).set_throttle_input(1.0)
        sample("gas")
        yield 6
    # Phase 2: brake to TURN_KMH, then full lock with half throttle for 4 s.
    for c in cars:
        mv(c).set_throttle_input(0.0)
        mv(c).set_brake_input(1.0)
    t1 = clock(world)
    while clock(world) - t1 < 10 and any(c.get_speed_kmh() > TURN_KMH for c in cars):
        for c in cars:
            if c.get_speed_kmh() <= TURN_KMH:
                mv(c).set_brake_input(0.0)
                mv(c).set_throttle_input(0.3)
        sample("rallenta")
        yield 6
    t2 = clock(world)
    while clock(world) - t2 < 4:
        for c in cars:
            mv(c).set_brake_input(0.0)
            mv(c).set_throttle_input(0.5)
            mv(c).set_steering_input(STEER)
        sample("curva")
        yield 6
    # Phase 3: straight, back up to speed, then full brake and stopping distance.
    for c in cars:
        mv(c).set_steering_input(0.0)
        mv(c).set_throttle_input(1.0)
    t3 = clock(world)
    while clock(world) - t3 < 6:
        sample("riprende")
        yield 6
    starts = {c.get_name(): (c.get_actor_location(), c.get_speed_kmh()) for c in cars}
    for c in cars:
        mv(c).set_throttle_input(0.0)
        mv(c).set_brake_input(1.0)
    t4 = clock(world)
    while clock(world) - t4 < 10 and any(c.get_speed_kmh() > 0.5 for c in cars):
        sample("frena")
        yield 6
    report = {}
    for c in cars:
        d = data[c.get_name()]
        s = d["samples"]
        gas = [x for x in s if x[0] == "gas"]
        def time_to(v):
            hit = next((x[1] for x in gas if x[2] >= v), None)
            return round(hit - gas[0][1], 1) if hit is not None and gas else None
        curve = [x for x in s if x[0] == "curva"]
        loc0, v0 = starts[c.get_name()]
        report[d["name"]] = {
            "0_30_s": time_to(30), "0_50_s": time_to(50), "0_80_s": time_to(80),
            "top_kmh": max((x[2] for x in gas), default=0), "top_gear": max((x[3] for x in gas), default=0),
            "max_rpm": max((x[4] for x in gas), default=0),
            "turn_speed_kmh": curve[0][2] if curve else None, "turn_max_roll_deg": max((abs(x[5]) for x in curve), default=0),
            "turn_min_upz": min((x[6] for x in curve), default=1), "tipped": any(x[6] < 0.5 for x in s),
            "brake_from_kmh": round(v0, 1), "brake_distance_m": round((c.get_actor_location() - loc0).length() / 100, 1),
            "samples": s[::4],
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
