"""Automatic test of health, stamina and death in the town (Play In Editor): sprint, a fall, run over by a
car, jumping out of a moving car, death (ragdoll, "SEI MORTO") and coming back at the start.
Output: Saved/Mazzarino80/Player/Test/vitals/*.png and vitals_test.json.
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
OUT = ROOT / "Saved/Mazzarino80/Player/Test/vitals"


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


def vit(pc):
    v = pc.get_vitals()
    if not v:
        return None
    return {k: round(v.get_editor_property(k), 1) for k in ("health", "armour", "stamina")} | {"dead": v.is_dead(), "exhausted": v.get_editor_property("bExhausted")}


def mappings():
    imc = unreal.load_asset("/Game/Input/IMC_Sandbox")
    out = []
    for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings") if hasattr(imc, "default_key_mappings") else imc.get_editor_property("mappings"):
        out.append([m.get_editor_property("action").get_name(), str(m.get_editor_property("key").get_editor_property("key_name"))])
    return out


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    report = {}
    try:
        report["imc_sandbox"] = mappings()
    except Exception as e:  # noqa: BLE001
        report["imc_sandbox"] = "error: %s" % e
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 900
    world = unreal.EditorLevelLibrary.get_game_world()
    if not world:
        raise RuntimeError("PIE did not start")
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    pawn = pc.get_controlled_pawn()
    report["pawn"] = pawn.get_class().get_name()
    report["start"] = vit(pc)
    start_loc = pawn.get_actor_location()

    # Sprint: hold forward with "Wants to Sprint" on (as holding Shift).
    report["sprint_control"] = pc.set_character_sprint(True)
    speeds = []
    fwd = pawn.get_actor_forward_vector()
    turn = [0.0]

    def setattr_fwd():
        nonlocal fwd
        turn[0] += 0.02
        fwd = unreal.Vector(math.cos(turn[0]), math.sin(turn[0]), 0)

    stam = []

    def push():
        pc.set_character_sprint(True)
        pawn.add_movement_input(fwd, 1.0)
        speeds.append(pawn.get_velocity().length())
        stam.append(vit(pc))
    # Run in a circle so the character does not hit a wall: turn the direction a little each frame.
    for s in wait(world, 11, lambda: (push(), setattr_fwd())):
        yield s
    report["sprint_speed_max"] = round(max(speeds or [0]))
    report["after_sprint_11s"] = vit(pc)
    report["first_exhausted_at"] = next((i for i, v in enumerate(stam) if v and v["exhausted"]), None)
    report["speed_when_exhausted"] = round(speeds[-1])
    for s in shot(world, "01_stamina", report):
        yield s
    pawn.set_actor_location(start_loc, False, True)
    yield 30

    # Fall from 8 m.
    pawn.set_actor_location(start_loc + unreal.Vector(0, 0, 800), False, True)
    for s in wait(world, 3):
        yield s
    report["after_fall_8m"] = vit(pc)
    for s in shot(world, "02_caduta", report):
        yield s

    # Run over by a car driving at the player.
    cars = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car))
    car = min(cars, key=lambda c: (c.get_actor_location() - pawn.get_actor_location()).length())
    report["car"] = car.get_name()
    cf = car.get_actor_forward_vector()
    pawn.set_actor_location(car.get_actor_location() + cf * 900 + unreal.Vector(0, 0, 60), False, True)
    yield 20
    mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    mv.set_handbrake_input(False)
    car.get_editor_property("mesh").set_physics_linear_velocity(cf * 900)  # ~32 km/h
    before = vit(pc)["health"]
    hit_t = []

    def drive():
        mv.set_throttle_input(1.0)
        v = vit(pc)
        if v and v["health"] < before and not hit_t:
            hit_t.append(round(car.get_speed_kmh(), 1))
    for s in wait(world, 2.5, drive):
        yield s
    mv.set_throttle_input(0.0)
    mv.set_brake_input(1.0)
    report["run_over_kmh"] = hit_t
    report["after_run_over"] = vit(pc)
    for s in shot(world, "03_investito", report):
        yield s
    for s in wait(world, 2):
        yield s
    mv.set_brake_input(0.0)

    # Jump out of a moving car.
    pawn = pc.get_controlled_pawn()
    door = car.get_actor_transform().transform_location(car.get_editor_property("door_offset"))
    pawn.set_actor_location(door + car.get_actor_right_vector() * -150 + unreal.Vector(0, 0, 40), False, True)
    yield 30
    pc.interact()
    for s in wait(world, 6):
        if pc.get_controlled_pawn() == car:
            break
        yield s
    report["got_in"] = pc.get_controlled_pawn() == car
    if report["got_in"]:
        before = vit(pc)
        cmv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
        for _ in range(20):
            cmv.set_handbrake_input(False)
            cmv.set_throttle_input(1.0)
            car.get_editor_property("mesh").set_physics_linear_velocity(car.get_actor_forward_vector() * 1250)  # 45 km/h
            yield 1
        report["jump_speed_kmh"] = round(car.get_speed_kmh(), 1)
        pc.interact()
        yield 15
        report["jumped_out"] = pc.get_controlled_pawn() != car
        report["after_jump"] = vit(pc)
        report["before_jump"] = before
        for s in shot(world, "04_salto_giu", report):
            yield s
        report["car_kmh_after_jump"] = round(car.get_speed_kmh(), 1)

    # Death and coming back.
    pawn = pc.get_controlled_pawn()
    money = pc.get_editor_property("money")
    pc.get_vitals().take_hit(500.0, unreal.Vector(1, 0, 0), None)
    report["dead_state"] = str(pc.get_editor_property("state"))
    for s in wait(world, 1.8):
        yield s
    for s in shot(world, "05_morto", report):
        yield s
    for s in wait(world, 4.4):
        yield s
    new = pc.get_controlled_pawn()
    report["respawned"] = bool(new) and new != pawn
    report["money_before_after"] = [money, pc.get_editor_property("money")]
    report["after_respawn"] = vit(pc)
    for s in wait(world, 1.6):
        yield s
    for s in shot(world, "06_ospedale", report):
        yield s
    (OUT / "vitals_test.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "vitals_test_error.txt"))
