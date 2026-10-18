"""Short Piaggio Si test in L_M80_ProvaMoto (Play In Editor), only what is being fixed:
1) riding: frame by frame, how far Vito's elbows jump between frames and how far his wrists are from the grips (Mano_L/R);
   close-ups of the hands;
2) into the wall from the start: the moped without its rider, every 0.1 s (lean, speed), photos of it falling;
3) picking it up from the ground and getting on: the moped's lean while it comes up, photos.
Output: Saved/Mazzarino80/Veicoli/TestMotorinoBreve/*.png and test.json (and the log's lines of the moped).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_motorino_test_breve.py -ForceLit
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
MAP = "/Game/Mazzarino80/Vehicles/Maps/L_M80_ProvaMoto"
OUT = ROOT / "Saved/Mazzarino80/Veicoli/TestMotorinoBreve"
V = unreal.Vector
CAM = []
r = {}


def save():
    (OUT / "test.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


def now(world):
    return unreal.GameplayStatics.get_time_seconds(world)


def wait(world, seconds, each=None):
    t0 = now(world)
    while now(world) - t0 < seconds:
        if each:
            each()
        yield 1


def state(pc):
    return str(pc.get_editor_property("state")).split(".")[-1].split(":")[0].upper()


def roll(car):
    return math.degrees(math.asin(max(-1.0, min(1.0, car.get_actor_right_vector().z))))


def around(car, fwd, side, up):
    return car.get_actor_location() + car.get_actor_forward_vector() * fwd + car.get_actor_right_vector() * side + V(0, 0, up)


def look(world, pc, at, eye, name, back_to):
    if not CAM:
        CAM.extend(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))
    cam = CAM[0]
    d = at - eye
    cam.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    yield 3
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1600x900")
    yield 30
    m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1)
    if back_to:
        pc.set_view_target_with_blend(back_to, 0.0)
    yield 2


def body_of(walker):
    """Vito's MetaHuman body: the mesh whose animation is UM80BodyAnimInstance (else the leader of the clothes)."""
    for c in walker.get_components_by_class(unreal.SkeletalMeshComponent):
        inst = c.get_anim_instance()
        if inst and inst.get_class().get_name() == "M80BodyAnimInstance":
            return c, "M80BodyAnimInstance"
    for c in walker.get_components_by_class(unreal.SkeletalMeshComponent):
        if "body" in c.get_name().lower():
            inst = c.get_anim_instance()
            return c, inst.get_class().get_name() if inst else None
    return None, None


def get_on(world, pc, car, tag, photos=False):
    t0 = now(world)
    while now(world) - t0 < 10 and (pc.get_player_character() is None or state(pc) != "ON_FOOT"):
        yield 1
    walker = pc.get_player_character()
    if not walker:
        r[tag + "_riding"] = False
        return
    f = car.get_actor_forward_vector()
    up = unreal.Transform(car.get_actor_location(), unreal.Rotator(0, 0, math.degrees(math.atan2(f.y, f.x))), V(1, 1, 1))
    door = up.transform_location(car.get_editor_property("door_offset"))
    walker.set_actor_location(door - up.transform_direction(V(0, 1, 0)) * 120 + V(0, 0, 60), False, True)
    for s in wait(world, 0.6):
        yield s
    r[tag + "_lying_before"] = car.is_lying_down()
    pc.interact()
    t0 = now(world)
    lean = []
    taken = 0
    while now(world) - t0 < 12 and pc.get_controlled_pawn() != car:
        lean.append([round(now(world) - t0, 2), round(car.get_actor_up_vector().z, 2)])
        if photos and taken < 4 and now(world) - t0 > 0.4 + taken * 0.6:
            taken += 1
            for s in look(world, pc, car.get_actor_location() + V(0, 0, 60), around(car, -220, -330, 170), "%s_%d" % (tag, taken), None):
                yield s
        yield 1
    r[tag + "_s"] = round(now(world) - t0, 2)
    r[tag + "_riding"] = pc.get_controlled_pawn() == car
    r[tag + "_moped_up_t"] = lean[::6]
    r[tag + "_upright_after"] = round(car.get_actor_up_vector().z, 3)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 400
    world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    bikes = {b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80CarPiaggioSi)}
    car = bikes.get("C_PiaggioSi")
    mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    for s in wait(world, 1.0):
        yield s
    start = car.get_actor_transform()

    # 1) Riding: elbows and wrists, frame by frame.
    for s in get_on(world, pc, car, "sale"):
        yield s
    save()
    walker = pc.get_player_character()
    body, anim = body_of(walker)
    r["body"] = [body.get_name() if body else None, anim]
    for s in wait(world, 4.0, lambda: mv.set_throttle_input(1.0)):
        yield s
    r["kmh_misura"] = round(car.get_speed_kmh(), 1)
    mesh = car.get_editor_property("mesh")
    rows = []
    t0 = now(world)
    while now(world) - t0 < 3.0 and body:
        mv.set_throttle_input(1.0)
        car.set_cart_input(0.0, 0.0, 0.12 * math.sin((now(world) - t0) * 2.0))
        tr = car.get_actor_transform()
        row = []
        for b, grip in (("lowerarm_l", None), ("lowerarm_r", None), ("hand_l", "Mano_L"), ("hand_r", "Mano_R")):
            p = tr.inverse_transform_location(body.get_socket_location(b))
            row.append(p)
            if grip:
                row.append((body.get_socket_location(b) - mesh.get_socket_location(grip)).length())
        for b in ("calf_l", "calf_r"):
            row.append(tr.inverse_transform_location(body.get_socket_location(b)))
        rows.append(row)
        yield 1
    if rows:
        jumps = {"gomito_l": 0.0, "gomito_r": 0.0, "ginocchio_l": 0.0, "ginocchio_r": 0.0}
        for a, b in zip(rows, rows[1:]):
            jumps["gomito_l"] = max(jumps["gomito_l"], (b[0] - a[0]).length())
            jumps["gomito_r"] = max(jumps["gomito_r"], (b[1] - a[1]).length())
            jumps["ginocchio_l"] = max(jumps["ginocchio_l"], (b[6] - a[6]).length())
            jumps["ginocchio_r"] = max(jumps["ginocchio_r"], (b[7] - a[7]).length())
        r["frames"] = len(rows)
        r["salto_max_gomito_cm_tra_frame"] = {k: round(v, 1) for k, v in jumps.items()}
        r["polso_manopola_cm"] = {"sinistra": [round(min(x[3] for x in rows), 1), round(max(x[3] for x in rows), 1)],
                                   "destra": [round(min(x[5] for x in rows), 1), round(max(x[5] for x in rows), 1)]}
    car.set_cart_input(0.0, 0.0, 0.0)
    for b, side in (("hand_l", -1), ("hand_r", 1)):
        h = body.get_socket_location(b) if body else car.get_actor_location()
        for s in look(world, pc, h, h + car.get_actor_right_vector() * (side * 45) + car.get_actor_forward_vector() * 25 + V(0, 0, 18), "1_mano_" + b[-1], car):
            yield s
    for s in look(world, pc, around(car, -10, 0, 90), around(car, 0, -300, 120), "1_lato", car):
        yield s
    save()

    # 2) Into the wall: the moped without its rider.
    car.set_actor_transform(start, False, True)
    mesh.set_physics_linear_velocity(V(0, 0, 0))
    mesh.set_physics_angular_velocity_in_degrees(V(0, 0, 0))
    for s in wait(world, 1.0):
        yield s
    line_y = car.get_actor_location().y
    t0 = now(world)
    while now(world) - t0 < 16 and pc.get_controlled_pawn() == car:
        mv.set_throttle_input(1.0)
        car.set_cart_input(0.0, 0.0, max(-0.3, min(0.3, (car.get_actor_location().y - line_y) * 0.004)))
        yield 1
    r["urto_buttato"] = pc.get_controlled_pawn() != car
    r["urto_perche"] = car.get_throw_reason()
    moped = []
    t0 = now(world)
    shots = [0.6, 2.5]
    while now(world) - t0 < 4.0:
        t = now(world) - t0
        moped.append([round(t, 2), round(car.get_actor_up_vector().z, 2), round(roll(car), 1), round(car.get_speed_kmh(), 1)])
        if shots and t > shots[0]:
            shots.pop(0)
            p = car.get_actor_location()
            for s in look(world, pc, p, p + V(-420, -300, 220), "2_moto_%.1fs" % t, None):
                yield s
        yield 1
    r["moto_dopo_urto_t_up_inclinazione_kmh"] = moped[::5]
    r["moto_a_terra"] = car.is_lying_down()
    save()

    # 3) Picking it up and getting on.
    for s in get_on(world, pc, car, "raccoglie", photos=True):
        yield s
    for s in wait(world, 0.5):
        yield s
    p = car.get_actor_location()
    for s in look(world, pc, p + V(0, 0, 80), around(car, -60, -320, 140), "3_in_sella", car):
        yield s
    save()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "errore.txt"))
