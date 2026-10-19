"""Every kind of vehicle in the drive test map L_M80_ProvaGuida (Play In Editor, the town's game mode): Vito walks up to
each one (Fiat 500, Ape, Piaggio Si, Alfa 155, the four soapbox carts), gets in or on with E, drives it for 4 s (throttle,
or pushing a cart), brakes to a stop and gets out. For each: got in, top speed, metres, got out on foot, how high the
feet went over the vehicle's base after getting out, the climbing caught nothing, alive.
M80_VEICOLI=D_Alfa155,E1 limits it to the vehicles whose label starts with those names.
Out: Saved/Mazzarino80/Veicoli/prova_veicoli.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_veicoli_prova_test.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Veicoli"
MAP = "/Game/Mazzarino80/Vehicles/L_M80_ProvaGuida"
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ONLY = [s for s in os.environ.get("M80_VEICOLI", "").split(",") if s]
r = {"veicoli": []}


def save():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prova_veicoli.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


def now(world):
    return unreal.GameplayStatics.get_time_seconds(world)


def name(v):
    return str(v).split(".")[-1].split(":")[0].split(">")[0].strip()


def wait(world, seconds, each=None):
    t0 = now(world)
    while now(world) - t0 < seconds:
        if each:
            each()
        yield 1


def drive(car, mv, cart, throttle, brake):
    if cart:
        car.set_cart_input(throttle, brake, 0.0)
    else:
        mv.set_throttle_input(throttle)
        mv.set_brake_input(brake)


def try_vehicle(world, pc, car, g):
    cart = isinstance(car, unreal.M80Carretto)
    mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    walker = pc.get_player_character()
    # By its left side (the driver's door, the moped's and carts' getting-on side), facing it.
    side = 200 if not cart and not car.is_two_wheeler() else 130
    walker.set_actor_location(car.get_actor_location() - car.get_actor_right_vector() * side + unreal.Vector(0, 0, 90), False, True)
    for _ in range(20):
        yield 1
    pc.interact()
    t0 = now(world)
    while now(world) - t0 < 12 and pc.get_controlled_pawn() != car:
        yield 1
    g["salito"] = pc.get_controlled_pawn() == car
    g["stato_dopo_salita"] = name(pc.get_editor_property("state"))
    if not g["salito"]:
        return
    for s in wait(world, 1.0):
        yield s
    start = car.get_actor_location()
    f0, t0, w0 = unreal.SystemLibrary.get_frame_count(), now(world), __import__("time").time()
    top = [0.0]
    for s in wait(world, 4.0, lambda: (drive(car, mv, cart, 1.0, 0.0), top.__setitem__(0, max(top[0], abs(car.get_speed_kmh()))))):
        yield s
    g["kmh_max"] = round(top[0], 1)
    g["metri"] = round((car.get_actor_location() - start).length() / 100, 1)
    g["frame_gioco_s_reale_s"] = [unreal.SystemLibrary.get_frame_count() - f0, round(now(world) - t0, 2), round(__import__("time").time() - w0, 1)]
    g["fisica"] = car.root_component.is_simulating_physics()
    trace, stopped = [], []
    tb = now(world)

    def braking():
        # Brake until it stands, then let go (S held on longer reverses or walks it back).
        if not stopped and abs(car.get_speed_kmh()) < 1.0:
            stopped.append(round(now(world) - tb, 1))
        drive(car, mv, cart, 0.0, 0.0 if stopped else 1.0)
        if not trace or now(world) - tb >= len(trace) * 0.5:
            trace.append([round(now(world) - tb, 1), round(car.get_speed_kmh(), 1), round(mv.get_brake_input(), 2), mv.get_current_gear()])
    for s in wait(world, 4.0, braking):
        yield s
    g["frenata_t_kmh_freno_marcia"] = trace
    g["fermo_dopo_s"] = stopped[0] if stopped else None
    drive(car, mv, cart, 0.0, 0.0)
    g["kmh_fermo"] = round(abs(car.get_speed_kmh()), 1)
    base = car.get_actor_location().z
    pc.interact()
    climb = walker.get_component_by_class(unreal.M80ClimbComponent)
    vitals = walker.get_component_by_class(unreal.M80VitalsComponent)
    half = walker.capsule_component.get_scaled_capsule_half_height()
    rise, states, climbs = -1e9, [], []
    t0 = now(world)
    while now(world) - t0 < 8:
        rise = max(rise, walker.get_actor_location().z - half - base)
        s, c = name(pc.get_editor_property("state")), name(climb.get_state()) if climb else "-"
        if not states or states[-1] != s:
            states.append(s)
        if not climbs or climbs[-1] != c:
            climbs.append(c)
        yield 1
    g.update({"stati_discesa": states, "arrampicata": climbs, "piedi_max_sopra_base_cm": round(rise),
              "sceso": states[-1] == "ON_FOOT" and pc.get_controlled_pawn() == walker,
              "morto": vitals.is_dead() if vitals else None})


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    LES.editor_request_begin_play()
    yield 30
    world = unreal.EditorLevelLibrary.get_game_world()
    while world is None or unreal.GameplayStatics.get_player_controller(world, 0) is None or \
            not hasattr(unreal.GameplayStatics.get_player_controller(world, 0), "get_player_character") or \
            unreal.GameplayStatics.get_player_controller(world, 0).get_player_character() is None:
        yield 5
        world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    for s in wait(world, 3.0):
        yield s
    cars = sorted(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car), key=lambda c: c.get_actor_label())
    for car in cars:
        label = car.get_actor_label()
        if ONLY and not any(label.startswith(o) for o in ONLY):
            continue
        g = {"veicolo": label}
        r["veicoli"].append(g)
        for s in try_vehicle(world, pc, car, g):
            yield s
        save()
        if g.get("morto"):
            break
        for s in wait(world, 1.0):
            yield s
    save()
    LES.editor_request_end_play()
    yield 30


m80_seq.Sequencer(steps(), log_file=str(OUT / "prova_veicoli_errore.txt"))
