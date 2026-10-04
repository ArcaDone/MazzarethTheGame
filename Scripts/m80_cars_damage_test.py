"""Automatic test of the GTA car features in the town (Play In Editor): getting into a locked car (window),
lights, horn and speedometer while driving, then shooting the car: smoke, fire, explosion, burnt shell.
Output: Saved/Mazzarino80/Player/Test/auto/*.png and cars_damage_test.json.
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
MAP = os.environ.get("M80_PLAY_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese")
OUT = ROOT / "Saved/Mazzarino80/Player/Test/auto"


def shot(world, name, report):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "shot showui")
    yield 30
    got = m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1)
    report.setdefault("shots", []).append([name, bool(got)])


def wait(world, seconds, each=None):
    t0 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t0 < seconds:
        if each:
            each()
        yield 1


def look(cam, pc, eye, target):
    d = target - eye
    cam.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
    pc.set_view_target_with_blend(cam, 0.0)


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
    start = pawn.get_actor_location()
    start_fwd = pawn.get_actor_forward_vector()
    cam = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))[0]
    cars = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car))
    report["locked"] = {c.get_name(): c.get_editor_property("bLocked") for c in cars}
    locked = [c for c in cars if c.get_editor_property("bLocked")]
    car = min(locked or cars, key=lambda c: (c.get_actor_location() - pawn.get_actor_location()).length())
    report["car"] = car.get_name()
    door = car.get_actor_transform().transform_location(car.get_editor_property("door_offset"))
    pawn.set_actor_location(door + car.get_actor_right_vector() * -200 + unreal.Vector(0, 0, 40), False, True)
    for s in wait(world, 1.0):
        yield s
    pc.interact()
    broke = False
    t0 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t0 < 8 and pc.get_controlled_pawn() != car:
        if not broke and not car.get_editor_property("bLocked"):
            broke = True
            for s in shot(world, "01_finestrino", report):
                yield s
        yield 2
    report["window_broken"] = broke
    report["driving"] = pc.get_controlled_pawn() == car
    # Drive with lights on, horn.
    car.toggle_lights()
    car.horn()
    mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    for s in wait(world, 2.5, lambda: mv.set_throttle_input(0.8)):
        yield s
    report["speed_kmh"] = round(car.get_speed_kmh(), 1)
    report["lights"] = car.are_lights_on()
    for s in shot(world, "02_guida_tachimetro", report):
        yield s
    mv.set_throttle_input(0.0)
    mv.set_brake_input(1.0)
    for s in wait(world, 2.5):
        yield s
    for s in shot(world, "03_luci_stop", report):
        yield s
    mv.set_brake_input(0.0)
    pc.interact()
    for s in wait(world, 1.0):
        yield s
    pawn = pc.get_controlled_pawn()
    # Step back from the door (the side the player got out: free), face the car and shoot it.
    out = pawn.get_actor_location() - car.get_actor_location()
    out.z = 0
    out = out.normal()
    pawn.set_actor_location(car.get_actor_location() + out * 450 + unreal.Vector(0, 0, 60), False, True)

    def face_car():
        d = car.get_actor_location() + unreal.Vector(0, 0, 40) - (pawn.get_actor_location() + unreal.Vector(0, 0, 60))
        pc.set_control_rotation(unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))))
    for s in wait(world, 1.0, face_car):
        yield s
    def above(c):
        # High over the roofs, looking down at the car and the player.
        target = (c.get_actor_location() + pawn.get_actor_location()) * 0.5
        look(cam, pc, target + out * 700 + unreal.Vector(0, 0, 1400), target)
    inv = pc.get_inventory()
    inv.give(unreal.M80Weapon.BERETTA, 90, True)
    for s in wait(world, 0.5, face_car):
        yield s
    h0 = car.get_editor_property("health")
    fired = 0
    t0 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t0 < 2.5:
        face_car()
        if inv.try_fire(car.get_actor_location() + unreal.Vector(0, 0, 40)):
            fired += 1
        yield 1
    report["shots_fired"] = fired
    report["health_after_shots"] = [round(h0), round(car.get_editor_property("health"))]
    above(car)
    yield 2
    for s in shot(world, "04_spari_auto", report):
        yield s
    cl = car.get_actor_location()
    # Damage stages (shots would take long): white smoke, black smoke, fire; then away and it blows up.
    for frac, name in ((0.4, "05_fumo_bianco"), (0.2, "06_fumo_nero"), (0.07, "07_fuoco")):
        hp = car.get_editor_property("health")
        unreal.GameplayStatics.apply_damage(car, hp - frac * car.get_editor_property("max_health"), pc, pawn, unreal.DamageType)
        for s in wait(world, 1.2, face_car):
            yield s
        above(car)
        yield 2
        for s in shot(world, name, report):
            yield s
        pc.set_view_target_with_blend(pawn, 0.0)
    pawn.set_actor_location(car.get_actor_location() + out * 800 + unreal.Vector(0, 0, 60), False, True)
    for s in wait(world, 4.5, face_car):
        yield s
    report["wrecked"] = car.get_editor_property("bWrecked")
    above(car)
    yield 2
    for s in shot(world, "08_esplosa", report):
        yield s
    for s in wait(world, 2.0):
        yield s
    above(car)
    yield 2
    for s in shot(world, "09_carcassa", report):
        yield s
    report["player_health"] = round(pc.get_vitals().get_editor_property("health"), 1) if pc.get_vitals() else None
    (OUT / "cars_damage_test.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "cars_damage_test_error.txt"))
