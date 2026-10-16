"""Fiat 500 test in L_M80_ProvaAzione (Play In Editor): the player walks to the car's door and gets in (E), photos while
getting in, from the chase camera, from the side and from the front with the driver seated, a short drive (throttle,
steering left and right, brake) between the houses, then out again.
Output: Saved/Mazzarino80/Veicoli/Test500/*.png and test_500.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_fiat500_test.py -ForceLit
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
MAP = "/Game/Mazzarino80/Player/Maps/L_M80_ProvaAzione"
OUT = ROOT / "Saved/Mazzarino80/Veicoli/Test500"
V = unreal.Vector


def now(world):
    return unreal.GameplayStatics.get_time_seconds(world)


def wait(world, seconds, each=None):
    t0 = now(world)
    while now(world) - t0 < seconds:
        if each:
            each()
        yield 1


def shot(world, name, report):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1600x900")
    yield 30
    got = m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1)
    report.setdefault("shots", []).append([name, bool(got)])


def around(car, fwd, side, up):
    return car.get_actor_location() + car.get_actor_forward_vector() * fwd + car.get_actor_right_vector() * side + V(0, 0, up)


def look(world, pc, at, eye, name, report, back_to):
    cams = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))
    cam = cams[0] if cams else world.spawn_actor(unreal.CameraActor, eye, unreal.Rotator())
    d = at - eye
    cam.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    yield 3
    for s in shot(world, name, report):
        yield s
    pc.set_view_target_with_blend(back_to, 0.0)
    yield 2


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    r = {}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 400
    world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    for atmo in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Atmosphere):
        atmo.set_editor_property("bAdvanceInGame", False)
        atmo.set_hour(16.5)
    cars = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80CarFiat500))
    r["cars"] = len(cars)
    if not cars:
        (OUT / "test_500.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        return
    car = cars[0]
    mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    pawn = pc.get_controlled_pawn()
    for s in wait(world, 1.0):
        yield s
    r["parked_upright"] = round(car.get_actor_up_vector().z, 3)
    r["parked_wheels_z_cm"] = round(car.get_actor_location().z, 1)
    for s in look(world, pc, around(car, 0, 0, 60), around(car, 420, -380, 220), "01_parcheggiata", r, pawn):
        yield s

    # The player's face and clothes, standing.
    head = pawn.get_editor_property("mesh").get_socket_location("head")
    fwd = pawn.get_actor_forward_vector()
    for s in look(world, pc, head + V(0, 0, 5), head + fwd * 70 + V(0, 0, 8), "00_viso", r, pawn):
        yield s
    for s in look(world, pc, head - V(0, 0, 70), head + fwd * 260 + V(0, 0, -40), "00_figura", r, pawn):
        yield s

    # 1) Walk up to the door and get in.
    door = car.get_actor_transform().transform_location(car.get_editor_property("door_offset"))
    pawn.set_actor_location(door - car.get_actor_right_vector() * 60 + V(0, 0, 60), False, True)
    for s in wait(world, 0.8):
        yield s
    r["in_reach"] = bool(pc.get_car_in_reach()) and pc.get_car_in_reach() == car
    pc.interact()
    t0 = now(world)
    halfway = False
    while now(world) - t0 < 8 and pc.get_controlled_pawn() != car:
        if not halfway and "GETTING_IN" in str(pc.get_editor_property("state")).upper() and pawn.get_attach_parent_actor() == car:
            halfway = True
            for s in look(world, pc, around(car, 0, 0, 60), around(car, -80, -330, 160), "02_sale", r, pawn):
                yield s
        yield 2
    r["get_in_s"] = round(now(world) - t0, 2)
    r["driving"] = pc.get_controlled_pawn() == car
    if not r["driving"]:
        (OUT / "test_500.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        return
    for s in wait(world, 1.5):
        yield s
    walker = pc.get_player_character()
    # Car-local x, y, z (cm; z = height above the ground): the roof is at 131 cm, the floor at about 22 cm.
    body = walker.get_editor_property("mesh") if walker else None
    if body:
        z0 = car.get_actor_location().z
        tr = car.get_actor_transform()
        r["seated_cm"] = {b: [round(c, 1) for c in (lambda p: (p.x, p.y, p.z))(tr.inverse_transform_location(body.get_socket_location(b)))]
                          for b in ("head", "pelvis", "foot_l", "foot_r", "ball_l", "ball_r") if body.does_socket_exist(b)}
    for s in shot(world, "03_camera_guida", r):
        yield s
    for s in look(world, pc, around(car, -20, 0, 80), around(car, -10, -260, 110), "04_lato", r, car):
        yield s
    for s in look(world, pc, around(car, -20, 0, 80), around(car, 330, -40, 150), "05_davanti", r, car):
        yield s

    # 2) A short drive between the houses: throttle, a bend each way, brake.
    start = car.get_actor_location()
    speeds = []
    for s in wait(world, 2.5, lambda: (mv.set_throttle_input(0.7), speeds.append(car.get_speed_kmh()))):
        yield s
    r["kmh_after_2_5s"] = round(speeds[-1], 1) if speeds else None
    r["gear"] = car.get_gear()
    for s in shot(world, "06_in_moto", r):
        yield s
    yaw0 = car.get_actor_rotation().yaw
    for s in wait(world, 1.2, lambda: (mv.set_throttle_input(0.4), car.set_cart_input(0.0, 0.0, -1.0))):
        yield s
    for s in wait(world, 1.2, lambda: (mv.set_throttle_input(0.4), car.set_cart_input(0.0, 0.0, 1.0))):
        yield s
    r["yaw_change"] = round(car.get_actor_rotation().yaw - yaw0, 1)
    car.set_cart_input(0.0, 0.0, 0.0)
    mv.set_throttle_input(0.0)
    v0 = car.get_speed_kmh()
    t1 = now(world)
    while now(world) - t1 < 5 and abs(car.get_speed_kmh()) > 0.5:
        mv.set_brake_input(1.0)
        yield 1
    mv.set_brake_input(0.0)
    r["brake_from_kmh"] = round(v0, 1)
    r["brake_s"] = round(now(world) - t1, 2)
    r["driven_m"] = round((car.get_actor_location() - start).length() / 100, 1)
    r["upright_after_drive"] = round(car.get_actor_up_vector().z, 3)

    # 3) Out again.
    pc.interact()
    for s in wait(world, 2.0):
        yield s
    r["on_foot_again"] = pc.get_controlled_pawn() != car
    walker = pc.get_player_character()
    if walker:
        r["off_distance_cm"] = round((walker.get_actor_location() - car.get_actor_location()).length())
        for s in look(world, pc, around(car, 0, 0, 60), around(car, -200, -420, 200), "07_sceso", r, walker):
            yield s
    (OUT / "test_500.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "test_500_errore.txt"))
