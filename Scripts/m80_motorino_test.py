"""Piaggio Si test in L_M80_ProvaMoto (Play In Editor; Scripts/m80_prova_moto_mappa.py makes the map): the player walks up and
gets on (E: the getting-on clip), rides off, leans into an S bend, stops (the left foot down), gets off (the clip) and on
again (how high the feet are over the road during both clips), walks it back with the feet (no reverse gear); three wheelies
from the start: the throttle held at a steady 0.6 (up and down again, a parabola), held by a steady hand (the throttle
following the angle), wide open (over backwards: thrown off, up again); full speed into the wall 80 m ahead (thrown over the
handlebar, up again); last, on and off the moped parked against the kerb (standing on the sidewalk, 15 cm up).
Output: Saved/Mazzarino80/Veicoli/TestMotorino/*.png and test_motorino.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_motorino_test.py -ForceLit
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
OUT = ROOT / "Saved/Mazzarino80/Veicoli/TestMotorino"
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


CAM = []


def look(world, pc, at, eye, name, report, back_to):
    if not CAM:
        CAM.extend(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))
    if not CAM:
        report.setdefault("no_camera", []).append(name)
        return
    cam = CAM[0]
    d = at - eye
    cam.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    yield 3
    for s in shot(world, name, report):
        yield s
    if back_to:
        pc.set_view_target_with_blend(back_to, 0.0)
    yield 2


def state(pc):
    return str(pc.get_editor_property("state")).split(".")[-1].split(":")[0].upper()


def roll(car):
    return math.degrees(math.asin(max(-1.0, min(1.0, car.get_actor_right_vector().z))))


def save(r):
    (OUT / "test_motorino.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


def feet_over_road(world, walker, car):
    """The lower ankle's height over the road under it (cm)."""
    body = walker.get_editor_property("mesh")
    best = None
    for b in ("foot_l", "foot_r"):
        p = body.get_socket_location(b)
        hit = unreal.SystemLibrary.line_trace_single(world, p + V(0, 0, 20), p - V(0, 0, 200), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                      False, [car, walker], unreal.DrawDebugTrace.NONE, True)
        t = hit.to_tuple() if hit else None
        if t and t[0]:
            h = p.z - t[4].z
            best = h if best is None else min(best, h)
    return best


def get_on(world, pc, car, r, tag, photos=False):
    t0 = now(world)
    while now(world) - t0 < 8 and (pc.get_player_character() is None or state(pc) != "ON_FOOT"):
        yield 1
    walker = pc.get_player_character()
    r[tag + "_state_before"] = state(pc)
    if walker is None:
        r[tag + "_riding"] = False
        return
    # Beside where it stands upright (also when it lies on its side: then it is picked up first).
    f = car.get_actor_forward_vector()
    yaw = math.degrees(math.atan2(f.y, f.x))
    up = unreal.Transform(car.get_actor_location(), unreal.Rotator(0, 0, yaw), V(1, 1, 1))
    door = up.transform_location(car.get_editor_property("door_offset"))
    side = up.transform_direction(V(0, 1, 0))
    r[tag + "_lying"] = car.is_lying_down()
    walker.set_actor_location(door - side * 120 + V(0, 0, 60), False, True)
    for s in wait(world, 0.6):
        yield s
    r[tag + "_in_reach"] = pc.get_car_in_reach() == car
    pc.interact()
    t0 = now(world)
    taken = 0
    feet = []
    lying = car.is_lying_down()
    while now(world) - t0 < 12 and pc.get_controlled_pawn() != car:
        if lying and photos and taken < 3 and now(world) - t0 > 0.6 + taken * 0.7:
            taken += 1
            for s in look(world, pc, car.get_actor_location() + V(0, 0, 60), around(car, 160, -330, 170), "%s_raccoglie_%d" % (tag, taken), r, None):
                yield s
        if walker.get_attach_parent_actor() == car:
            h = feet_over_road(world, walker, car)
            if h is not None:
                feet.append(round(h, 1))
            if photos and taken < 3 and now(world) - t0 > 0.5 + taken * 0.8:
                taken += 1
                for s in look(world, pc, around(car, -20, 0, 90), around(car, 160, -330, 170), "%s_sale_%d" % (tag, taken), r, None):
                    yield s
        yield 1
    r[tag + "_get_on_s"] = round(now(world) - t0, 2)
    r[tag + "_riding"] = pc.get_controlled_pawn() == car
    r[tag + "_upright_after"] = round(car.get_actor_up_vector().z, 3)
    # While standing beside it the lower ankle should be ~8-10 cm over the road.
    half = feet[:len(feet) // 2]
    r[tag + "_feet_over_road_cm_first_half"] = [min(half or [0]), max(half or [0])]


def get_off(world, pc, car, r, tag, photos=True):
    walker = pc.get_player_character()
    pc.interact()
    feet = []
    t0 = now(world)
    taken = False
    while now(world) - t0 < 4 and state(pc) != "ON_FOOT":
        h = feet_over_road(world, walker, car) if walker else None
        if h is not None:
            feet.append(round(h, 1))
        if photos and not taken and now(world) - t0 > 1.3:
            taken = True
            for s in look(world, pc, around(car, -20, 0, 90), around(car, 160, -330, 170), tag + "_scende", r, None):
                yield s
        yield 1
    r[tag + "_off_state"] = state(pc)
    half = feet[len(feet) // 2:]
    r[tag + "_feet_over_road_cm_second_half"] = [min(half or [0]), max(half or [0])]
    for s in wait(world, 0.8):
        yield s
    walker = pc.get_player_character()
    if walker:
        r[tag + "_off_beside_cm"] = [round(c) for c in (lambda p: (p.x, p.y, p.z))(car.get_actor_transform().inverse_transform_location(walker.get_actor_location()))]
        if photos:
            for s in look(world, pc, around(car, 0, 0, 80), around(car, 200, -360, 170), tag + "_sceso", r, walker):
                yield s


def thrown(world, pc, car, r, tag):
    """Waits for the rider to come off; photos of the fall and of getting up."""
    t0 = now(world)
    while now(world) - t0 < 4 and pc.get_controlled_pawn() == car:
        yield 1
    r[tag + "_thrown"] = pc.get_controlled_pawn() != car
    r[tag + "_why"] = car.get_throw_reason()
    walker = pc.get_player_character()
    if not r[tag + "_thrown"] or not walker:
        return
    for s in wait(world, 0.4):
        yield s
    p = walker.get_editor_property("mesh").get_socket_location("pelvis")
    for s in look(world, pc, p, p + V(300, 300, 220), tag + "_caduta", r, None):
        yield s
    t1 = now(world)
    moped = r.setdefault(tag + "_moped_t_up_roll_kmh", [])
    last = -1.0
    while now(world) - t1 < 8 and state(pc) != "ON_FOOT":
        if now(world) - last > 0.4:
            last = now(world)
            mesh = car.get_editor_property("mesh")
            root_up = mesh.get_socket_transform("Root", unreal.RelativeTransformSpace.RTS_WORLD).transform_direction(V(0, 0, 1)).z
            moped.append([round(last - t0, 1), round(car.get_actor_up_vector().z, 2), round(roll(car), 1), round(car.get_speed_kmh(), 1),
                          "root_up", round(root_up, 2), "sim", mesh.is_simulating_physics(), "comp_up", round(mesh.get_up_vector().z, 2)])
        yield 1
    r[tag + "_up_after_s"] = round(now(world) - t0, 1)
    r[tag + "_final_state"] = state(pc)
    for s in wait(world, 1.5):
        yield s
    walker = pc.get_player_character()
    if walker:
        p = walker.get_actor_location()
        for s in look(world, pc, p, p + V(320, 280, 120), tag + "_rialzato", r, walker):
            yield s
    r[tag + "_moped_up"] = round(car.get_actor_up_vector().z, 2)
    r[tag + "_moped_roll"] = round(roll(car), 1)


def back_to_start(world, pc, car, mv, start):
    car.set_actor_transform(start, False, True)
    car.get_editor_property("mesh").set_physics_linear_velocity(V(0, 0, 0))
    car.get_editor_property("mesh").set_physics_angular_velocity_in_degrees(V(0, 0, 0))
    mv.set_throttle_input(0.0)
    for s in wait(world, 1.0):
        yield s


def wheelie(world, pc, car, mv, r, tag, throttle):
    """Rolls up to ~15 km/h, pulls; throttle: a number, or None for a steady hand holding it at ~20 degrees."""
    t0 = now(world)
    while now(world) - t0 < 5 and car.get_speed_kmh() < 15:
        mv.set_throttle_input(0.8)
        yield 1
    r[tag + "_kmh_at_pull"] = round(car.get_speed_kmh(), 1)
    log = []
    car.wheelie()
    top, up_s, last = 0.0, 0.0, now(world)
    t0 = now(world)
    shot_taken = False
    prev = 0.0
    while now(world) - t0 < 4.0 and pc.get_controlled_pawn() == car:
        d = car.get_wheelie_deg()
        if throttle is None:
            # A steady hand: more throttle when it sinks, less when it climbs.
            rate = (d - prev) / max(1e-3, now(world) - last)
            th = max(0.0, min(1.0, 0.6 + (20.0 - d) * 0.03 - rate * 0.008))
        else:
            th = throttle
        prev = d
        mv.set_throttle_input(th)
        t = now(world)
        if d > 2:
            up_s += t - last
        last = t
        top = max(top, d)
        p = math.degrees(math.asin(max(-1.0, min(1.0, car.get_actor_forward_vector().z))))
        log.append([round(t - t0, 2), round(car.get_speed_kmh(), 1), round(d, 1), round(p, 1), round(roll(car), 1), round(car.get_rider_lean(), 1), round(th, 2), state(pc)[:6]])
        if d > 15 and not shot_taken and throttle is not None:
            shot_taken = True
            for s in look(world, pc, around(car, 0, 0, 80), around(car, 50, -420, 120), tag + "_impennata", r, car):
                yield s
        yield 1
    mv.set_throttle_input(0.0)
    r[tag + "_top_deg"] = round(top, 1)
    r[tag + "_up_s"] = round(up_s, 2)
    r[tag + "_diario"] = log[::3]


def stop(world, car, mv):
    t0 = now(world)
    mv.set_throttle_input(0.0)
    while now(world) - t0 < 5 and abs(car.get_speed_kmh()) > 0.5:
        mv.set_brake_input(1.0)
        yield 1
    mv.set_brake_input(0.0)


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
    bikes = {b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80CarPiaggioSi)}
    r["bikes"] = sorted(bikes)
    car = bikes.get("C_PiaggioSi")
    if not car:
        save(r)
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        return
    mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    for s in wait(world, 1.0):
        yield s
    start = car.get_actor_transform()
    r["parked_upright"] = round(car.get_actor_up_vector().z, 3)
    for s in look(world, pc, around(car, 0, 0, 60), around(car, 260, -260, 160), "01_parcheggiato", r, pc.get_controlled_pawn()):
        yield s

    # 1) On (photos of the clip), riding photos.
    for s in get_on(world, pc, car, r, "02", photos=True):
        yield s
    if not r["02_riding"]:
        save(r)
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        return
    for s in wait(world, 1.0):
        yield s
    for s in look(world, pc, around(car, -10, 0, 90), around(car, 0, -280, 120), "03_in_sella_lato", r, car):
        yield s
    for s in look(world, pc, around(car, 0, 0, 100), around(car, 300, -60, 150), "04_in_sella_davanti", r, car):
        yield s
    body = pc.get_player_character().get_editor_property("mesh")
    for b, side in (("hand_l", -1), ("hand_r", 1)):
        h = body.get_socket_location(b)
        eye = h + car.get_actor_right_vector() * (side * 45) + car.get_actor_forward_vector() * 25 + V(0, 0, 18)
        for s in look(world, pc, h, eye, "04_mano_" + b[-1], r, car):
            yield s

    # 2) Off it goes; an S bend: how far it leans.
    speeds = []
    for s in wait(world, 4.0, lambda: (mv.set_throttle_input(1.0), speeds.append(car.get_speed_kmh()))):
        yield s
    r["kmh_after_4s"] = round(speeds[-1], 1) if speeds else None
    for s in shot(world, "05_in_moto", r):
        yield s
    leans = []
    for s in wait(world, 1.2, lambda: (mv.set_throttle_input(0.9), car.set_cart_input(0.0, 0.0, 0.5), leans.append(roll(car)))):
        yield s
    r["lean_deg_right_bend"] = round(min(leans), 1) if leans else None
    r["kmh_in_bend"] = round(car.get_speed_kmh(), 1)
    for s in look(world, pc, around(car, 0, 0, 80), around(car, -320, 30, 120), "06_piega_da_dietro", r, car):
        yield s
    leans = []
    for s in wait(world, 1.2, lambda: (mv.set_throttle_input(0.9), car.set_cart_input(0.0, 0.0, -0.5), leans.append(roll(car)))):
        yield s
    r["lean_deg_left_bend"] = round(max(leans), 1) if leans else None
    car.set_cart_input(0.0, 0.0, 0.0)
    for s in stop(world, car, mv):
        yield s
    for s in wait(world, 1.0):
        yield s
    r["stopped_upright"] = round(car.get_actor_up_vector().z, 3)
    for s in look(world, pc, around(car, 0, 0, 50), around(car, 60, -300, 90), "07_fermo_piede_a_terra", r, car):
        yield s
    save(r)

    # 3) Off (the clip) and on again.
    for s in get_off(world, pc, car, r, "08"):
        yield s
    for s in get_on(world, pc, car, r, "10", photos=True):
        yield s

    # 4) Back with the feet (S held, stopped).
    p0 = car.get_actor_location()
    back = []
    t0 = now(world)
    shot_taken = False
    while now(world) - t0 < 2.5:
        car.set_cart_input(0.0, 1.0, 0.0)
        back.append(car.get_speed_kmh())
        if now(world) - t0 > 1.2 and not shot_taken:
            shot_taken = True
            for s in look(world, pc, around(car, 0, 0, 50), around(car, 80, -300, 90), "11_indietro_coi_piedi", r, car):
                yield s
        yield 1
    r["11_backing"] = car.is_backing_up()
    car.set_cart_input(0.0, 0.0, 0.0)
    d = car.get_actor_location() - p0
    f = car.get_actor_forward_vector()
    r["11_back_cm"] = round(-(d.x * f.x + d.y * f.y))
    r["11_back_kmh_min"] = round(min(back), 1) if back else None
    save(r)

    # 5) Wheelies, each from the start.
    for tag, th in (("12_parabola", 0.6), ("13_tenuta", None), ("14_troppo_gas", 1.0)):
        if pc.get_controlled_pawn() != car:
            for s in get_on(world, pc, car, r, tag + "_risale"):
                yield s
        if pc.get_controlled_pawn() != car:
            break
        for s in back_to_start(world, pc, car, mv, start):
            yield s
        for s in wheelie(world, pc, car, mv, r, tag, th):
            yield s
        if pc.get_controlled_pawn() == car:
            for s in stop(world, car, mv):
                yield s
        else:
            for s in thrown(world, pc, car, r, tag):
                yield s
            for s in wait(world, 2.0):
                yield s
            r[tag + "_moped_lying"] = car.is_lying_down()
            p = car.get_actor_location()
            for s in look(world, pc, p, p + V(-250, -300, 180), tag + "_moto_a_terra", r, None):
                yield s
        save(r)

    # 6) Into the wall from the start, full throttle.
    if pc.get_controlled_pawn() != car:
        for s in get_on(world, pc, car, r, "15_risale"):
            yield s
    if pc.get_controlled_pawn() == car:
        for s in back_to_start(world, pc, car, mv, start):
            yield s
        hit_kmh = []
        t0 = now(world)
        line_y = car.get_actor_location().y
        while now(world) - t0 < 16 and pc.get_controlled_pawn() == car:
            mv.set_throttle_input(1.0)
            # Holding the line to the wall (+X): a little steering against the drift.
            car.set_cart_input(0.0, 0.0, max(-0.3, min(0.3, (car.get_actor_location().y - line_y) * 0.004)))
            hit_kmh.append(car.get_speed_kmh())
            yield 1
        r["15_top_kmh"] = round(max(hit_kmh), 1) if hit_kmh else None
        e = car.get_actor_location()
        r["15_end_cm"] = [round(e.x), round(e.y), round(e.z)]
        for s in thrown(world, pc, car, r, "15_muro"):
            yield s
        for s in wait(world, 2.0):
            yield s
        r["15_muro_moped_lying"] = car.is_lying_down()
        p = car.get_actor_location()
        for s in look(world, pc, p, p + V(-250, -300, 180), "15_moto_a_terra", r, None):
            yield s
        if r["15_muro_moped_lying"]:
            for s in get_on(world, pc, car, r, "15b_raccolta", photos=True):
                yield s
            if pc.get_controlled_pawn() == car:
                for s in wait(world, 0.8):
                    yield s
                for s in get_off(world, pc, car, r, "15c", photos=False):
                    yield s
    save(r)

    # 7) The moped by the kerb: on and off standing on the sidewalk.
    kerb = bikes.get("C_PiaggioSi_Marciapiede")
    if kerb:
        for s in get_on(world, pc, kerb, r, "16_marciapiede", photos=True):
            yield s
        if pc.get_controlled_pawn() == kerb:
            for s in wait(world, 0.8):
                yield s
            for s in get_off(world, pc, kerb, r, "17_marciapiede"):
                yield s
    save(r)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "test_motorino_errore.txt"))
