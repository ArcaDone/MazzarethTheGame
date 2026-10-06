"""Automatic play test of the town (Play In Editor): spawn, walk to a car, get in with E, drive, get out,
full map. Screenshots with the HUD (console "shot showui") and a side view of the seated driver.
Output: Saved/Mazzarino80/Player/Test/*.png and play_test.json.
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
MAP = os.environ.get("M80_PLAY_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese_WP")
OUT = ROOT / "Saved/Mazzarino80/Player/Test" / os.environ.get("M80_PLAY_CAR", "auto")


def shot(world, name, report):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "shot showui")
    yield 30
    got = m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1)
    report.setdefault("shots", []).append([name, bool(got)])


def side_view(world, pc, car):
    """Looks at the car from the driver side through a camera of the map (PIE copy)."""
    cams = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))
    if not cams:
        return False
    cam = cams[0]
    loc = car.get_actor_location()
    right = car.get_actor_right_vector()
    eye = loc - right * 380 + unreal.Vector(0, 0, 110)
    d = loc + unreal.Vector(0, 0, 70) - eye
    rot = unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x)))
    cam.set_actor_location_and_rotation(eye, rot, False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    return True


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    report = {}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 900
    world = unreal.EditorLevelLibrary.get_game_world()
    if not world:
        raise RuntimeError("PIE did not start")
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    pawn = pc.get_controlled_pawn()
    report["controller"] = pc.get_class().get_name()
    report["pawn"] = pawn.get_class().get_name() if pawn else None
    report["hud"] = pc.get_hud().get_class().get_name() if pc.get_hud() else None
    for s in shot(world, "01_a_piedi", report):
        yield s
    cams = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))
    if cams:
        for name, dist, side, height, tz in (("00_ritratto", 230, 0, 30, 20), ("00_viso", 75, 15, 72, 72)):
            fwd = pawn.get_actor_forward_vector()
            right = pawn.get_actor_right_vector()
            target = pawn.get_actor_location() + unreal.Vector(0, 0, tz)
            eye = pawn.get_actor_location() + fwd * dist + right * side + unreal.Vector(0, 0, height)
            d = target - eye
            cams[0].set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
            pc.set_view_target_with_blend(cams[0], 0.0)
            yield 20
            for s in shot(world, name, report):
                yield s
        pc.set_view_target_with_blend(pawn, 0.0)
        yield 10
    # Walk next to the nearest car if it is not in reach yet.
    cars = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car))
    report["cars"] = [c.get_name() for c in cars]
    want = os.environ.get("M80_PLAY_CAR", "")
    pool = [c for c in cars if want in c.get_name()] or cars
    car = min(pool, key=lambda c: (c.get_actor_location() - pawn.get_actor_location()).length())
    report["car"] = car.get_name()
    if (car.get_actor_location() - pawn.get_actor_location()).length() > 400:
        door = car.get_actor_transform().transform_location(car.get_editor_property("door_offset"))
        pawn.set_actor_location(door + car.get_actor_right_vector() * -250 + unreal.Vector(0, 0, 40), False, True)
        yield 60
    for s in shot(world, "02_vicino_auto", report):
        yield s
    report["in_reach"] = pc.get_car_in_reach().get_name() if hasattr(pc, "get_car_in_reach") and pc.get_car_in_reach() else None
    pc.interact()
    t0 = unreal.GameplayStatics.get_time_seconds(world)
    states = []
    while unreal.GameplayStatics.get_time_seconds(world) - t0 < 8:
        states.append(str(pc.get_editor_property("state")))
        if pc.get_controlled_pawn() == car:
            break
        yield 5
    report["get_in_states"] = sorted(set(states))
    report["driving"] = pc.get_controlled_pawn() == car
    yield 60
    walker = pc.get_player_character()
    if walker:
        mesh = walker.get_editor_property("mesh")
        inv = car.get_actor_transform()
        bones = {}
        for b in ("pelvis", "head", "foot_l", "ball_l", "hand_l"):
            w = mesh.get_socket_location(b)
            l = inv.inverse_transform_location(w)
            bones[b] = [round(l.x), round(l.y), round(l.z)]
        o, e = car.get_actor_bounds(True)
        lo = inv.inverse_transform_location(o)
        bones["car_center_local"] = [round(lo.x), round(lo.y), round(lo.z)]
        bones["car_extent"] = [round(e.x), round(e.y), round(e.z)]
        bones["anim_mode"] = str(mesh.get_animation_mode())
        report["seat_bones_local"] = bones
    if side_view(world, pc, car):
        yield 20
        for s in shot(world, "03_seduto_lato", report):
            yield s
        pc.set_view_target_with_blend(car, 0.0)
        yield 10
    for s in shot(world, "04_in_auto", report):
        yield s
    mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    t1 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t1 < 3:
        mv.set_throttle_input(0.6)
        yield 3
    report["speed_after_3s"] = round(car.get_speed_kmh(), 1)
    for s in shot(world, "05_guida", report):
        yield s
    mv.set_throttle_input(0.0)
    mv.set_brake_input(1.0)
    t2 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t2 < 4 and abs(car.get_speed_kmh()) > 2:
        yield 5
    mv.set_brake_input(0.0)
    pc.interact()
    yield 90
    report["on_foot_again"] = pc.get_controlled_pawn() != car
    for s in shot(world, "06_sceso", report):
        yield s
    pc.toggle_map()
    yield 10
    for s in shot(world, "07_mappa", report):
        yield s
    pc.toggle_map()
    (OUT / "play_test.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "play_test_error.txt"))
