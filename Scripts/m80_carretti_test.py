"""Soapbox cart test in L_M80_ProvaCarretti (Play In Editor), for each of the four carts: walk to it and get on (E),
photos of the rider from the side and from the front, where the hands and feet are against the cart's grips, push on
the flat (top speed), steer (the hands follow the rope / bar / handle), brake, shuffle back, then down the 10% ramp
from the platform (top speed, how far it rolls) and get off.
Output: Saved/Mazzarino80/Carretti/Test/*.png and carretti_test.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_carretti_test.py -ForceLit
Env M80_CARRETTI=Cuscinetti,Persiana limits the carts.
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
MAP = "/Game/Mazzarino80/Vehicles/Maps/L_M80_ProvaCarretti"
OUT = ROOT / "Saved/Mazzarino80/Carretti/Test"
V = unreal.Vector
ONLY = [k for k in os.environ.get("M80_CARRETTI", "").split(",") if k]


def shot(world, name, report):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1600x900")
    yield 30
    got = m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1)
    report.setdefault("shots", []).append([name, bool(got)])


def wait(world, seconds, each=None):
    t0 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t0 < seconds:
        if each:
            each()
        yield 1


def look(world, pc, at, eye, name, report, back_to):
    cam = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))[0]
    d = at - eye
    cam.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    yield 3
    for s in shot(world, name, report):
        yield s
    pc.set_view_target_with_blend(back_to, 0.0)
    yield 2


def around(car, fwd, side, up):
    return car.get_actor_location() + car.get_actor_forward_vector() * fwd + car.get_actor_right_vector() * side + V(0, 0, up)


def limbs(walker, car):
    """Distance (cm) of each wrist / ankle of the posed copy and of the visible body from the cart's grips."""
    cm = car.get_editor_property("mesh")
    out = {}
    meshes = walker.get_components_by_class(unreal.SkeletalMeshComponent)
    for comp in meshes:
        tag = "copia" if "M80Overlay" in [str(t) for t in comp.component_tags] else comp.get_name()
        if not comp.does_socket_exist("hand_l"):
            continue
        row = {}
        for bone, grip in (("hand_l", "Mano_L"), ("hand_r", "Mano_R"), ("foot_l", "Piede_L"), ("foot_r", "Piede_R")):
            if cm.does_socket_exist(grip) and comp.does_socket_exist(bone):
                row[bone] = round((comp.get_socket_location(bone) - cm.get_socket_location(grip)).length(), 1)
        out[tag] = row
    return out


def ride(world, pc, car, key, report):
    r = {}
    pawn = pc.get_controlled_pawn()
    mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    # 1) Walk to it and get on.
    door = car.get_actor_transform().transform_location(car.get_editor_property("door_offset"))
    pawn.set_actor_location(door - car.get_actor_right_vector() * 60 + V(0, 0, 60), False, True)
    for s in wait(world, 0.8):
        yield s
    r["in_reach"] = bool(pc.get_car_in_reach()) and pc.get_car_in_reach() == car
    pc.interact()
    t0 = unreal.GameplayStatics.get_time_seconds(world)
    halfway = False
    while unreal.GameplayStatics.get_time_seconds(world) - t0 < 8 and pc.get_controlled_pawn() != car:
        if not halfway and "GETTING_IN" in str(pc.get_editor_property("state")).upper() and pawn.get_attach_parent_actor() == car:
            halfway = True
            for s in look(world, pc, around(car, 0, 0, 40), around(car, -60, -260, 120), "%s_01_sale" % key, report, pawn):
                yield s
        yield 2
    r["driving"] = pc.get_controlled_pawn() == car
    if not r["driving"]:
        report[key] = r
        return
    for s in wait(world, 1.0):
        yield s
    walker = pc.get_player_character()
    r["anim_mode"] = str(walker.get_editor_property("mesh").get_animation_mode())
    r["limbs_cm"] = limbs(walker, car)
    for s in look(world, pc, around(car, 0, 0, 35), around(car, -20, -230, 70), "%s_02_lato" % key, report, car):
        yield s
    for s in look(world, pc, around(car, 0, 0, 35), around(car, 200, -150, 140), "%s_03_davanti" % key, report, car):
        yield s

    # 2) Push on the flat: top speed.
    start = car.get_actor_location()
    speeds = []
    for s in wait(world, 6.0, lambda: (car.set_cart_input(1.0, 0.0, 0.0), speeds.append(car.get_speed_kmh()))):
        yield s
    r["push_kmh_1s_3s_6s"] = [round(speeds[min(len(speeds) - 1, int(len(speeds) * f))], 1) for f in (1 / 6, 0.5, 0.999)]
    r["push_metres"] = round((car.get_actor_location() - start).length() / 100, 1)
    for s in shot(world, "%s_04_spinta" % key, report):
        yield s

    # 3) Steer left while pushing: the hands go with the rope / bar / handle.
    yaw0 = car.get_actor_rotation().yaw
    for s in wait(world, 1.2, lambda: car.set_cart_input(1.0, 0.0, -1.0)):
        yield s
    r["steer_left_yaw"] = round(car.get_actor_rotation().yaw - yaw0, 1)
    r["limbs_steering_cm"] = limbs(walker, car)
    for s in look(world, pc, around(car, 10, 0, 30), around(car, 160, -120, 120), "%s_05_sterza" % key, report, car):
        yield s

    # 4) Brake, then shuffle back.
    car.set_cart_input(0.0, 0.0, 0.0)
    v0 = car.get_speed_kmh()
    p0 = car.get_actor_location()
    t1 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t1 < 6 and car.get_speed_kmh() > 0.5:
        car.set_cart_input(0.0, 1.0, 0.0)
        yield 1
    r["brake_from_kmh"] = round(v0, 1)
    r["brake_s"] = round(unreal.GameplayStatics.get_time_seconds(world) - t1, 2)
    r["brake_m"] = round((car.get_actor_location() - p0).length() / 100, 2)
    for s in wait(world, 2.0, lambda: car.set_cart_input(0.0, 1.0, 0.0)):
        yield s
    r["back_kmh"] = round(car.get_speed_kmh(), 1)
    car.set_cart_input(0.0, 0.0, 0.0)

    # 5) Down the ramp: from the platform, a push, then it rolls by itself.
    car.set_actor_location_and_rotation(V(-3500, 0, 330), unreal.Rotator(0, 0, 0), False, True)
    car.put_back_on_wheels()
    for s in wait(world, 1.0):
        yield s
    track = []
    top = [0.0]
    mid_shot = [False]

    def roll():
        k = car.get_speed_kmh()
        top[0] = max(top[0], k)
        p = car.get_actor_location()
        track.append([round(p.x), round(p.z), round(k, 1)])
        car.set_cart_input(1.0 if p.x < -2900 else 0.0, 0.0, 0.0)
    t2 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t2 < 25:
        roll()
        p = car.get_actor_location()
        if not mid_shot[0] and p.x > -1500:
            mid_shot[0] = True
            for s in shot(world, "%s_06_discesa" % key, report):
                yield s
        if unreal.GameplayStatics.get_time_seconds(world) - t2 > 4 and car.get_speed_kmh() < 0.5:
            break
        yield 1
    r["ramp_top_kmh"] = round(top[0], 1)
    r["ramp_kmh_at_foot"] = next((t[2] for t in track if t[0] >= 0), None)
    r["ramp_rolled_on_flat_m"] = round(max(0.0, car.get_actor_location().x) / 100, 1)
    r["ramp_track"] = track[::20]
    r["upright"] = round(car.get_actor_up_vector().z, 3)

    # 6) Get off.
    car.set_cart_input(0.0, 1.0, 0.0)
    for s in wait(world, 2.0):
        yield s
    car.set_cart_input(0.0, 0.0, 0.0)
    pc.interact()
    for s in wait(world, 1.2):
        yield s
    r["on_foot_again"] = pc.get_controlled_pawn() != car
    walker = pc.get_player_character()
    if walker:
        r["off_distance_cm"] = round((walker.get_actor_location() - car.get_actor_location()).length())
        for s in look(world, pc, around(car, 0, 0, 60), around(car, -150, -350, 180), "%s_07_sceso" % key, report, walker):
            yield s
    report[key] = r


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    report = {}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 600
    world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    # Loading the map in Play takes minutes of game clock: a fixed summer afternoon for the photos.
    for atmo in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Atmosphere):
        atmo.set_editor_property("bAdvanceInGame", False)
        atmo.set_hour(16.5)
    carts = {c.get_class().get_name().replace("M80Carretto", ""): c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Carretto)}
    report["carts"] = sorted(carts)
    for key in ["Cuscinetti", "Triangolo", "Cassetta", "Persiana"]:
        if (ONLY and key not in ONLY) or key not in carts:
            continue
        for s in ride(world, pc, carts[key], key, report):
            yield s
        (OUT / "carretti_test.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    (OUT / "carretti_test.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "carretti_test_error.txt"))
