"""Handling test in the test level (Play In Editor): for each car and speed, full steering (as with the
keyboard) for 3 s, a quick lane change left-right, full steering with full throttle. Measures the slip angle (angle between where the
car points and where it goes): a spin is a slip above 45 degrees.
Report: Saved/Mazzarino80/Vehicles/handling[_TAG].json (env M80_HANDLING_TAG).
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
TAG = os.environ.get("M80_HANDLING_TAG", "")
OUT = ROOT / "Saved/Mazzarino80/Vehicles" / ("handling%s.json" % ("_" + TAG if TAG else ""))
# Every run starts here: open ground, far from the ramps, walls and cones of the test track.
START = unreal.Vector(60000, 15000, 100)
SPEEDS = {"Fiat126": [40, 60, 80], "Ape": [30, 45], "Panda": [40, 60, 80], "Fiat127": [40, 60, 80], "FiatUno": [40, 60, 80],
          "Golf": [40, 70, 100], "Vespa": [30, 50]}


def mv(c):
    return c.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)


def slip(c):
    v = c.get_velocity()
    if v.length() < 150:
        return 0.0
    f = c.get_actor_forward_vector()
    a = math.degrees(math.atan2(f.x * v.y - f.y * v.x, f.x * v.x + f.y * v.y))
    if c.get_speed_kmh() < 0:
        a = 180 - abs(a)
    return a


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 300
    world = unreal.EditorLevelLibrary.get_game_world()
    if not world:
        raise RuntimeError("PIE did not start")
    clock = unreal.GameplayStatics.get_time_seconds
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    if pc:
        pc.un_possess()
    cars = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car))
    homes = {c.get_name(): (c.get_actor_location(), c.get_actor_rotation()) for c in cars}
    # Park everybody far apart: each car runs alone.
    for i, c in enumerate(cars):
        mv(c).set_requires_controller_for_inputs(False)
    report = {}
    for c in cars:
        kind = next((k for k in SPEEDS if k in c.get_class().get_name()), None)
        if not kind:
            continue
        others = [o for o in cars if o != c]
        for o in others:
            o.set_actor_location(o.get_actor_location() + unreal.Vector(0, 0, -5000), False, True)
            o.get_editor_property("mesh").set_simulate_physics(False)
        loc, rot = homes[c.get_name()]
        res = {}
        for kmh in SPEEDS[kind]:
            for test in ("sterzo_pieno", "cambio_corsia", "curva_gas"):
                c.set_actor_location_and_rotation(START, unreal.Rotator(0, 0, 0), False, True)
                m = c.get_editor_property("mesh")
                m.set_physics_linear_velocity(unreal.Vector(0, 0, 0))
                m.set_physics_angular_velocity_in_degrees(unreal.Vector(0, 0, 0))
                mv(c).reset_vehicle()
                mv(c).set_handbrake_input(False)
                mv(c).set_brake_input(0.0)
                mv(c).set_steering_input(0.0)
                yield 10
                # Get to speed with the engine, straight on.
                t0 = clock(world)
                while clock(world) - t0 < 25.0 and c.get_speed_kmh() < kmh:
                    mv(c).set_throttle_input(1.0)
                    mv(c).set_steering_input(0.0)
                    yield 1
                v0 = round(c.get_speed_kmh(), 1)
                yaw0 = c.get_actor_rotation().yaw
                slips, upz = [], []
                t1 = clock(world)
                while clock(world) - t1 < 3.0:
                    t = clock(world) - t1
                    if test == "cambio_corsia":
                        s = 1.0 if t < 0.6 else (-1.0 if t < 1.2 else 0.0)
                    else:
                        s = 1.0
                    mv(c).set_steering_input(s)
                    mv(c).set_throttle_input(1.0 if test == "curva_gas" else 0.5)
                    slips.append(abs(slip(c)))
                    upz.append(c.get_actor_up_vector().z)
                    yield 1
                yaw = (c.get_actor_rotation().yaw - yaw0 + 540) % 360 - 180
                res["%s_%d" % (test, kmh)] = {"start_kmh": v0, "max_slip_deg": round(max(slips or [0]), 1),
                                              "spin": max(slips or [0]) > 45, "tipped": min(upz or [1]) < 0.5,
                                              "end_kmh": round(c.get_speed_kmh(), 1), "yaw_change_deg": round(yaw, 1)}
                mv(c).set_throttle_input(0.0)
                mv(c).set_steering_input(0.0)
        report[kind] = res
        for o in others:
            o.get_editor_property("mesh").set_simulate_physics(True)
            l2, r2 = homes[o.get_name()]
            o.set_actor_location_and_rotation(l2 + unreal.Vector(0, 0, 30), r2, False, True)
        c.set_actor_location_and_rotation(loc + unreal.Vector(0, 0, 30), rot, False, True)
        yield 30
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
